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
	"time"
)

const logExpectedErr = "Got expected error: %v"

const (
	flagKind     = "--kind"
	testDataFile = "data.txt"
)

func TestVerifyAcceptsArtifactOrBundle(t *testing.T) {
	// 1. Create Artifact
	tmp := t.TempDir()
	storeDir := filepath.Join(tmp, "store")
	payload := filepath.Join(tmp, "payload.txt")
	os.WriteFile(payload, []byte("content"), 0644)

	// Pack (Standard Artifact)
	t.Setenv(EnvPolicyMode, "local")
	runPack([]string{flagKind, "compat", "--store", storeDir, payload})

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "compat"))
	artifactPath := filepath.Join(storeDir, "packs", "compat", entries[0].Name())

	// Verify Artifact (Regression)
	if err := verifyPack(VerifyConfig{Path: artifactPath, RepoRoot: ".", PolicyMode: "local"}); err != nil {
		t.Fatalf("Failed to verify standard artifact: %v", err)
	}

	// 2. Create Bundle
	// We need a dummy policy/key setup for bundle creation?
	// runBundle requires flags.
	// We'll skip signing for this test to keep it simple, or use dummy key?
	// If we skip signing, bundle verification will pass if policy allows.
	// Default permissive policy allows unsigned in local.
	bundlePath := filepath.Join(tmp, "bundle.tar.gz")

	// We need keys dir for runBundle even if empty?
	// "keys-dir" default is ops/keys/reviewpack.
	// runBundle logic: "Find key used in signature".
	// If no signature, keys copying is skipped.
	// Policy is copied.

	// Create dummy policy
	policyFile := filepath.Join(tmp, "policy.toml")
	os.WriteFile(policyFile, []byte("version=1\n[enforcement]\nlocal='permissive'\n"), 0644)

	err := runBundle([]string{
		"--artifact", artifactPath,
		"--policy", policyFile,
		"--out", bundlePath,
		// keys-dir defaults to non-existent, should be fine if no sig
	})
	if err != nil {
		t.Fatalf("Failed to create bundle: %v", err)
	}

	// Verify Bundle (New Feature)
	if err := verifyPack(VerifyConfig{Path: bundlePath, RepoRoot: ".", PolicyMode: "local"}); err != nil {
		t.Fatalf("Failed to verify bundle: %v", err)
	}
}

func TestRoundTripOK(t *testing.T) {
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")

	// Create payload
	if err := os.MkdirAll(payloadDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadDir, "file1.txt"), []byte("content1"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(payloadDir, "subdir"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadDir, "subdir", "file2.txt"), []byte("content2"), 0644); err != nil {
		t.Fatal(err)
	}

	// Pack
	cfg := PackConfig{
		Kind:      "test_kind",
		StoreDir:  storeDir,
		Payloads:  []string{payloadDir},
		Timestamp: time.Now().UTC(),
	}
	if _, err := executePack(cfg); err != nil {
		t.Fatalf("Pack failed: %v", err)
	}

	// Find the pack
	packsDir := filepath.Join(storeDir, "packs", "test_kind")
	entries, err := os.ReadDir(packsDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 {
		t.Fatalf("Expected 1 pack, got %d", len(entries))
	}
	packPath := filepath.Join(packsDir, entries[0].Name())

	// Verify
	if err := verifyPack(VerifyConfig{Path: packPath, RepoRoot: ".", PolicyMode: "local"}); err != nil {
		t.Fatalf("Verify failed: %v", err)
	}
}

func TestVerifyFailsOnCorruptDataFile(t *testing.T) {
	// 1. Create valid pack
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, testDataFile), []byte("original"), 0644)

	cfg := PackConfig{Kind: "test", StoreDir: storeDir, Payloads: []string{payloadDir}, Timestamp: time.Now()}
	executePack(cfg)

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "test"))
	if len(entries) == 0 {
		t.Fatal("Pack not created")
	}
	packPath := filepath.Join(storeDir, "packs", "test", entries[0].Name())

	// Integration test style:
	// 1. Pack normally.
	// 2. Open the tar, read all headers/files.
	// 3. Rewrite tar, but change content of one data file without updating manifest.
	// 4. Verify -> FAIL.

	modifyTar(t, packPath, func(name string, content []byte) []byte {
		if strings.Contains(name, testDataFile) {
			return []byte("corrupted")
		}
		return content
	}, nil)

	if err := verifyPack(VerifyConfig{Path: packPath, RepoRoot: ".", PolicyMode: "local"}); err == nil {
		t.Fatal("Expected verify to fail on corrupted data, but it passed")
	} else if !strings.Contains(err.Error(), "mismatch") { // hash mismatch
		t.Logf(logExpectedErr, err)
	}
}

func TestVerifyFailsOnSymlink(t *testing.T) {
	packPath := filepath.Join(t.TempDir(), "symlink.tar.gz")

	createManualTar(t, packPath, func(tw *tar.Writer) {
		writeTarFile(t, tw, "EVIDENCE_VERSION", "v1\n")
		// Add symlink
		hdr := &tar.Header{
			Name:     "data/symlink",
			Typeflag: tar.TypeSymlink,
			Linkname: "/etc/passwd",
			Mode:     0777,
		}
		tw.WriteHeader(hdr)
	})

	if err := verifyPack(VerifyConfig{Path: packPath, RepoRoot: ".", PolicyMode: "local"}); err == nil {
		t.Fatal("Expected verify failure on symlink, passed")
	} else {
		t.Logf(logExpectedErr, err)
	}
}

func TestVerifyFailsOnPathTraversal(t *testing.T) {
	packPath := filepath.Join(t.TempDir(), "traversal.tar.gz")

	createManualTar(t, packPath, func(tw *tar.Writer) {
		writeTarFile(t, tw, "EVIDENCE_VERSION", "v1\n")
		hdr := &tar.Header{
			Name: "../escape.txt",
			Mode: 0644,
			Size: 4,
		}
		tw.WriteHeader(hdr)
		tw.Write([]byte("test"))
	})

	if err := verifyPack(VerifyConfig{Path: packPath, RepoRoot: ".", PolicyMode: "local"}); err == nil {
		t.Fatal("Expected verify failure on path traversal, passed")
	} else {
		t.Logf(logExpectedErr, err)
	}
}

func TestVerifyFailsOnExtraFile(t *testing.T) {
	// Case: File in data/ but not in MANIFEST
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, "ok.txt"), []byte("ok"), 0644)

	cfg := PackConfig{Kind: "test", StoreDir: storeDir, Payloads: []string{payloadDir}, Timestamp: time.Now()}
	executePack(cfg)

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "test"))
	packPath := filepath.Join(storeDir, "packs", "test", entries[0].Name())

	modifyTar(t, packPath, func(name string, content []byte) []byte {
		return content
	}, func(tw *tar.Writer) {
		// Inject extra file
		writeTarFile(t, tw, "data/extra.txt", "I am extra")
	})

	if err := verifyPack(VerifyConfig{Path: packPath, RepoRoot: ".", PolicyMode: "local"}); err == nil {
		t.Fatal("Expected verify failure on extra file, passed")
	} else {
		t.Logf(logExpectedErr, err)
	}
}

func TestVerifyFailsOnExtraRootEntry(t *testing.T) {
	// Case: Extra file in ROOT (forbidden by strict contract)
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, "ok.txt"), []byte("ok"), 0644)

	cfg := PackConfig{Kind: "test", StoreDir: storeDir, Payloads: []string{payloadDir}, Timestamp: time.Now()}
	executePack(cfg)

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "test"))
	packPath := filepath.Join(storeDir, "packs", "test", entries[0].Name())

	modifyTar(t, packPath, func(name string, content []byte) []byte {
		return content
	}, func(tw *tar.Writer) {
		// Inject extra ROOT file
		writeTarFile(t, tw, "ROOT_EXTRA.txt", "I am forbidden in root")
	})

	if err := verifyPack(VerifyConfig{Path: packPath, RepoRoot: ".", PolicyMode: "local"}); err == nil {
		t.Fatal("Expected verify failure on extra root file, passed")
	} else if !strings.Contains(err.Error(), "forbidden root entry") {
		t.Fatalf("Got unexpected error: %v", err)
	} else {
		t.Logf(logExpectedErr, err)
	}
}

func TestPackRejectsInvalidKind(t *testing.T) {
	// Test runPack entry point kind validation

	// We run runPack with invalid arg
	t.Setenv(EnvPolicyMode, "local")
	err := runPack([]string{flagKind, "invalid-kind!", "."})
	if err == nil {
		t.Fatal("Expected runPack to fail on invalid kind")
	} else if !strings.Contains(err.Error(), "invalid kind") {
		t.Logf("Got error but maybe not kind validation? %v", err)
	} else {
		t.Logf("Got expected kind error: %v", err)
	}

	err = runPack([]string{flagKind, "../../traversal", "."})
	if err == nil {
		t.Fatal("Expected runPack to fail on traversal kind")
	} else {
		t.Logf("Got expected kind error: %v", err)
	}
}

func TestS7SigningRoundTrip(t *testing.T) {
	// Setup
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, testDataFile), []byte("signed data"), 0644)

	// User Payload
	// We need to simulate running pack with signing.
	// 1. Generate Key
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	privPath := filepath.Join(tmpDir, "priv.key")
	os.WriteFile(privPath, []byte(base64.StdEncoding.EncodeToString(priv)), 0600)

	// 2. Setup Repo Root for Public Key
	// runPack looks in ./ops/keys/reviewpack
	// We must change Cwd or pass repoRoot logic.
	// runPack uses "." as repoRoot internally (hardcoded in my implementation).
	// So we must run test in a dir that has ops/keys/reviewpack.

	wd, _ := os.Getwd()
	defer os.Chdir(wd)
	os.Chdir(tmpDir)

	os.MkdirAll(filepath.Join("ops", "keys", "reviewpack"), 0755)

	keyID := "s7-test-key"
	pubMeta := CryptoKey{
		KeyID: keyID, Alg: AlgEd25519, PubB64: base64.StdEncoding.EncodeToString(pub),
	}
	pubJSON, _ := json.Marshal(pubMeta)
	os.WriteFile(filepath.Join("ops", "keys", "reviewpack", keyID+".pub"), pubJSON, 0644)

	// S14-11: Provide dummy policy for post-pack verify (CI mode requirement)
	policyContent := `version=1
[enforcement]
mode_local='permissive'
mode_ci='strict'
`
	os.WriteFile(filepath.Join("ops", "reviewpack_policy.toml"), []byte(policyContent), 0644)

	// 3. Run Pack with Sign

	// Note: NewAuditLogger will try to create directory in Cwd (tmpDir).
	// That's fine.

	t.Setenv(EnvPolicyMode, "local")
	err := runPack([]string{
		flagKind, "s7test",
		"--store", storeDir,
		"--sign",
		"--key-file", privPath,
		payloadDir,
	})
	if err != nil {
		t.Fatalf("runPack with sign failed: %v", err)
	}

	// 4. Verify Sidecar Exists
	matches, _ := filepath.Glob(filepath.Join(storeDir, "packs/s7test/*.tar.gz.sig.json"))
	if len(matches) != 1 {
		t.Fatalf("Expected 1 sig file, got %d", len(matches))
	}
	sigPath := matches[0]
	packPath := strings.TrimSuffix(sigPath, ".sig.json")
	// 5. Verify Command (should pass)
	if err := runVerify([]string{"--pack", packPath}); err != nil {
		t.Fatalf("runVerify failed: %v", err)
	}

	// 6. Tampering Test: Modify Artifact
	// Append byte to tar
	f, _ := os.OpenFile(packPath, os.O_APPEND|os.O_WRONLY, 0644)
	f.Write([]byte{0x00})
	f.Close()

	if err := runVerify([]string{"--pack", packPath}); err == nil {
		t.Fatal("Expected verify to fail on tampered artifact, passed")
	} else if !strings.Contains(err.Error(), "artifact mismatch") {
		t.Logf(logExpectedErr, err)
	}

	// Restore Artifact
	// (Too hard to restore easily without backup, let's repack for next test or make new)

	// 7. Test Audit Log
	auditPath := ".local/reviewpack_audit/audit.log.jsonl"
	content, err := os.ReadFile(auditPath)
	if err != nil {
		t.Fatal("Audit log not found")
	}
	if !strings.Contains(string(content), "sign") || !strings.Contains(string(content), "verify") {
		t.Errorf("Audit log missing events. Content:\n%s", string(content))
	}
}

// Helpers for test

func createManualTar(t *testing.T, path string, fn func(*tar.Writer)) {
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	gw := gzip.NewWriter(f)
	defer gw.Close()
	tw := tar.NewWriter(gw)
	defer tw.Close()
	fn(tw)
}

func writeTarFile(t *testing.T, tw *tar.Writer, name, content string) {
	hdr := &tar.Header{
		Name: name,
		Mode: 0644,
		Size: int64(len(content)),
	}
	if err := tw.WriteHeader(hdr); err != nil {
		t.Fatal(err)
	}
	if _, err := tw.Write([]byte(content)); err != nil {
		t.Fatal(err)
	}
}

// tarItem holds a single tar entry for modification.
type tarItem struct {
	Header  *tar.Header
	Content []byte
}

// readTarItems reads all entries from a gzipped tar file.
func readTarItems(t *testing.T, path string) []tarItem {
	f, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()

	gzr, err := gzip.NewReader(f)
	if err != nil {
		t.Fatal(err)
	}
	defer gzr.Close()

	var items []tarItem
	tr := tar.NewReader(gzr)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			t.Fatal(err)
		}
		content, err := io.ReadAll(tr)
		if err != nil {
			t.Fatal(err)
		}
		items = append(items, tarItem{hdr, content})
	}
	return items
}

// modifyTar reads a tar, allows modifying content of existing files, or injecting new ones.
func modifyTar(t *testing.T, path string, modifier func(name string, content []byte) []byte, injectors func(*tar.Writer)) {
	items := readTarItems(t, path)

	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	gzw := gzip.NewWriter(f)
	defer gzw.Close()
	tw := tar.NewWriter(gzw)
	defer tw.Close()

	for _, it := range items {
		newContent := it.Content
		if modifier != nil {
			newContent = modifier(it.Header.Name, it.Content)
		}
		it.Header.Size = int64(len(newContent))
		if err := tw.WriteHeader(it.Header); err != nil {
			t.Fatal(err)
		}
		tw.Write(newContent)
	}

	if injectors != nil {
		injectors(tw)
	}
}
