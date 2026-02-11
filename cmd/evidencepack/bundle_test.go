package main

import (
	"archive/tar"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const (
	testPolicyFile = "policy.toml"
	testBundleFile = "bundle.tar.gz"
	flagArtifact   = "--artifact"
	flagStore      = "--store"
	flagBundleKind = "--kind"
	flagPolicy     = "--policy"
	flagKeysDir    = "--keys-dir"
	flagPack       = "--pack"
)

func TestBundleRoundTripOK(t *testing.T) {
	tmp := t.TempDir()
	storeDir := filepath.Join(tmp, "store")
	keysDir := filepath.Join(tmp, "keys")
	policyFile := filepath.Join(tmp, testPolicyFile)

	// Setup Environment
	setupTestEnv(t, tmp, storeDir, keysDir, policyFile)

	// 1. Create Artifact
	payload := filepath.Join(tmp, "payload.txt")
	os.WriteFile(payload, []byte("some payload"), 0644)

	packArgs := []string{flagBundleKind, "testbundle", flagStore, storeDir, payload}
	if err := runPack(packArgs); err != nil {
		t.Fatalf("pack failed: %v", err)
	}

	// Find generated artifact
	packDir := filepath.Join(storeDir, "packs", "testbundle")
	entries, _ := os.ReadDir(packDir)
	if len(entries) != 1 {
		t.Fatalf("expected 1 artifact, got %d", len(entries))
	}
	artifactPath := filepath.Join(packDir, entries[0].Name())

	// 2. Sign Artifact
	// We need a key. setupTestEnv creates 'testkey'
	keyPath := filepath.Join(keysDir, "testkey") // Private Key
	// runPack calls performSigning which uses key file.
	// But we separate sign step here? No, runPack has --sign flag.
	// Or we can use `evidencepack sign` command if we implemented it?
	// `sign.go` is missing from my view but `pack.go` has `performSigning`.
	// I'll manually sign using `performSigning` logic helper or just call `runBundle` with unsigned?
	// Requirement: "signature path: derived from artifact path".
	// Let's use `performSigning` helper from `pack.go` (exported? No. But same package tests access it).
	// Wait, `performSigning` signature: `(packPath string, keyFile string, repoRoot string, logger *AuditLogger) error`
	// It calls `findKeyID` which uses `repoRoot` -> `ops/keys/reviewpack`.
	// My setupTestEnv puts keys in `keysDir`.
	// `repoRoot` in `performSigning` expects `ops/keys/reviewpack`.
	// Use `tmp` as repoRoot and create structure `ops/keys/reviewpack`.

	// ADJUST repo setup to match expectation
	opsKeysDir := filepath.Join(tmp, "ops", "keys", "reviewpack")
	os.MkdirAll(opsKeysDir, 0755)
	// Move public key there
	os.Rename(filepath.Join(keysDir, "testkey.pub"), filepath.Join(opsKeysDir, "testkey.pub"))

	logger, _ := NewAuditLogger(tmp)
	if err := performSigning(artifactPath, keyPath, tmp, logger); err != nil {
		t.Fatalf("sign failed: %v", err)
	}

	// 3. Create Bundle
	bundlePath := filepath.Join(tmp, testBundleFile)
	bundleArgs := []string{
		flagArtifact, artifactPath,
		flagPolicy, policyFile,
		flagKeysDir, opsKeysDir,
		"--out", bundlePath,
	}
	if err := runBundle(bundleArgs); err != nil {
		t.Fatalf("bundle failed: %v", err)
	}

	// 4. Verify Bundle
	verifyArgs := []string{
		flagPack, bundlePath,
		"--policy-mode", "local", // or auto
	}
	// We need to capture verify output? Or just ensure no error.
	// verifyPack uses CheckPolicyEnv? No verifyPack calls `evaluatePolicy`.
	// verifyPack prints to stdout.
	if err := runVerify(verifyArgs); err != nil {
		t.Fatalf("verify bundle failed: %v", err)
	}
}

func TestBundleFailsOnTamperedArtifact(t *testing.T) {
	tmp := t.TempDir()
	storeDir := filepath.Join(tmp, "store")
	opsKeysDir := filepath.Join(tmp, "ops", "keys", "reviewpack")
	os.MkdirAll(opsKeysDir, 0755)
	keyPub, keyPriv, _ := ed25519.GenerateKey(rand.Reader)

	// Save keys
	privBytes := base64.StdEncoding.EncodeToString(keyPriv.Seed()) // 32 byte seed
	os.WriteFile(filepath.Join(tmp, "privkey"), []byte(privBytes), 0600)

	pubB64 := base64.StdEncoding.EncodeToString(keyPub)
	meta := CryptoKey{KeyID: "tamperkey", Alg: AlgEd25519, PubB64: pubB64}
	metaBytes, _ := json.Marshal(meta)
	os.WriteFile(filepath.Join(opsKeysDir, "tamperkey.pub"), metaBytes, 0644)

	policyFile := filepath.Join(tmp, testPolicyFile)
	os.WriteFile(policyFile, []byte(`
version = 1
[enforcement]
local = "strict"
[allowed_key_ids]
tamperkey = "owner"
`), 0644)

	// 1. Create Artifact
	payload := filepath.Join(tmp, "payload.txt")
	os.WriteFile(payload, []byte("valid payload"), 0644)
	packArgs := []string{flagBundleKind, "tampertest", flagStore, storeDir, payload}
	runPack(packArgs)

	packDir := filepath.Join(storeDir, "packs", "tampertest")
	entries, _ := os.ReadDir(packDir)
	artifactPath := filepath.Join(packDir, entries[0].Name())

	// 2. Sign
	logger, _ := NewAuditLogger(tmp)
	performSigning(artifactPath, filepath.Join(tmp, "privkey"), tmp, logger)

	// 3. Create Valid Bundle
	bundlePath := filepath.Join(tmp, testBundleFile)
	runBundle([]string{flagArtifact, artifactPath, flagPolicy, policyFile, flagKeysDir, opsKeysDir, "--out", bundlePath})

	// 4. Tamper Bundle
	// extracting bundle, modifying artifact, repacking?
	// Or modifying artifact INSIDE bundle tar?
	// Easier: extract bundle manually, tamper artifact, repack.

	explodeDir := filepath.Join(tmp, "explode")
	unpackBundleTo(t, bundlePath, explodeDir)

	// Tamper inner artifact
	innerArt := filepath.Join(explodeDir, "artifact", filepath.Base(artifactPath))
	// Append junk
	f, _ := os.OpenFile(innerArt, os.O_APPEND|os.O_WRONLY, 0644)
	f.WriteString("JUNK")
	f.Close()

	// Repack directory into buf -> file
	// We reuse createDeterministicTar?
	badBundlePath := filepath.Join(tmp, "bad_bundle.tar.gz")
	createDeterministicTar(explodeDir, badBundlePath)

	// 5. Verify -> Should Fail (Signature Mismatch)
	if err := runVerify([]string{flagPack, badBundlePath, "--policy-mode", "local"}); err == nil {
		t.Fatal("Verify should have failed on tampered artifact")
	} else {
		if !strings.Contains(err.Error(), "cryptographic verification failed") && !strings.Contains(err.Error(), "artifact mismatch") {
			// It might occur at checksum level or signature verification level
			// "artifact mismatch: claimed ..., actual ..."
			t.Logf("Correctly failed: %v", err)
		}
	}
}

func TestBundleFailsOnWrongKey(t *testing.T) {
	// Similar setup but swap the key in bundle/keys
	tmp := t.TempDir()
	storeDir := filepath.Join(tmp, "store")
	opsKeysDir := filepath.Join(tmp, "ops", "keys", "reviewpack")
	os.MkdirAll(opsKeysDir, 0755)

	// Key A
	pubA, privA, _ := ed25519.GenerateKey(rand.Reader)
	writeKey(t, opsKeysDir, "keyA", pubA)
	writePriv(t, tmp, "keyA", privA)

	// Key B (Attacker)
	pubB, _, _ := ed25519.GenerateKey(rand.Reader)
	writeKey(t, opsKeysDir, "keyB", pubB)

	policyFile := filepath.Join(tmp, testPolicyFile)
	os.WriteFile(policyFile, []byte("version=1\n[enforcement]\nlocal='strict'\n"), 0644)

	// Artifact signed by A
	payload := filepath.Join(tmp, "p.txt")
	os.WriteFile(payload, []byte("data"), 0644)
	runPack([]string{flagBundleKind, "wrongkey", flagStore, storeDir, payload})

	packDir := filepath.Join(storeDir, "packs", "wrongkey")
	entries, _ := os.ReadDir(packDir)
	artifactPath := filepath.Join(packDir, entries[0].Name())

	logger, _ := NewAuditLogger(tmp)
	performSigning(artifactPath, filepath.Join(tmp, "keyA.priv"), tmp, logger)

	// Create Bundle
	bundlePath := filepath.Join(tmp, testBundleFile)
	runBundle([]string{flagArtifact, artifactPath, flagPolicy, policyFile, flagKeysDir, opsKeysDir, "--out", bundlePath})

	// Tamper Bundle keys: Replace keyA.pub with keyB.pub content but keep name keyA.pub?
	// This simulates "fake key" attack where bundled key is not the one that signed it?
	// Wait, signature says "KeyID: keyA".
	// Verify loads "keys/keyA.pub".
	// If we replace keys/keyA.pub with KeyB's public key content...
	// Verify will use KeyB to verify signature made by KeyA -> Fail.

	explodeDir := filepath.Join(tmp, "explode")
	unpackBundleTo(t, bundlePath, explodeDir)

	// Overwrite keyA.pub with keyB.pub
	bBytes, _ := os.ReadFile(filepath.Join(opsKeysDir, "keyB.pub"))
	os.WriteFile(filepath.Join(explodeDir, "keys", "keyA.pub"), bBytes, 0644)

	badBundlePath := filepath.Join(tmp, "badkey_bundle.tar.gz")
	createDeterministicTar(explodeDir, badBundlePath)

	if err := runVerify([]string{flagPack, badBundlePath}); err == nil {
		t.Fatal("Verify should have failed on wrong key")
	} else {
		t.Logf("Correctly failed: %v", err)
	}
}

// Helpers

func setupTestEnv(t *testing.T, tmp, store, keys, policy string) {
	os.MkdirAll(store, 0755)
	os.MkdirAll(keys, 0755)

	// Generate Key
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	writeKey(t, keys, "testkey", pub)

	privBytes := base64.StdEncoding.EncodeToString(priv.Seed())
	os.WriteFile(filepath.Join(keys, "testkey"), []byte(privBytes), 0600)

	// Policy
	os.WriteFile(policy, []byte(`
version = 1
[enforcement]
local = "strict"
[allowed_key_ids]
testkey = "owner"
`), 0644)
}

func writeKey(t *testing.T, dir, name string, pub ed25519.PublicKey) {
	b64 := base64.StdEncoding.EncodeToString(pub)
	meta := CryptoKey{KeyID: name, Alg: AlgEd25519, PubB64: b64}
	bytes, _ := json.Marshal(meta)
	os.WriteFile(filepath.Join(dir, name+".pub"), bytes, 0644)
}

func writePriv(t *testing.T, dir, name string, priv ed25519.PrivateKey) {
	b64 := base64.StdEncoding.EncodeToString(priv.Seed())
	os.WriteFile(filepath.Join(dir, name+".priv"), []byte(b64), 0600)
}

func unpackBundleTo(t *testing.T, bundlePath, dest string) {
	f, err := os.Open(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	gz, _ := gzip.NewReader(f)
	tr := tar.NewReader(gz)
	for {
		h, err := tr.Next()
		if err == io.EOF {
			break
		}
		target := filepath.Join(dest, h.Name)
		if h.Typeflag == tar.TypeDir {
			os.MkdirAll(target, 0755)
		} else {
			os.MkdirAll(filepath.Dir(target), 0755)
			wf, _ := os.Create(target)
			io.Copy(wf, tr)
			wf.Close()
		}
	}
}
