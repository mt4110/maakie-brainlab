package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestCanonicalMessage(t *testing.T) {
	artSHA := "abc"
	chkSHA := "def"
	expected := "reviewpack.sig.v1\nartifact_sha256=abc\nchecksums_sha256=def\n"

	msg := CanonicalMessage(artSHA, chkSHA)
	if string(msg) != expected {
		t.Errorf("CanonicalMessage mismatch.\nGot: %q\nWant: %q", string(msg), expected)
	}
}

func TestKeyUtils(t *testing.T) {
	// Generate a key
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)

	// Save private key to file (base64)
	privB64 := base64.StdEncoding.EncodeToString(priv)
	tmpFile := filepath.Join(t.TempDir(), "priv.key")
	os.WriteFile(tmpFile, []byte(privB64), 0600)

	// Load Private
	loadedPriv, err := LoadPrivateKey(tmpFile)
	if err != nil {
		t.Fatalf("LoadPrivateKey failed: %v", err)
	}
	if !loadedPriv.Equal(priv) {
		t.Error("Loaded private key mismatch")
	}

	// Test Env loading
	os.Setenv("REVIEWPACK_PRIVATE_KEY_B64", privB64)
	defer os.Unsetenv("REVIEWPACK_PRIVATE_KEY_B64")

	loadedPrivEnv, err := LoadPrivateKey("")
	if err != nil {
		t.Fatalf("LoadPrivateKey(Env) failed: %v", err)
	}
	if !loadedPrivEnv.Equal(priv) {
		t.Error("Loaded private key (env) mismatch")
	}

	// Find Key ID (Mock repo root)
	// We need to create ops/keys/reviewpack/key.pub
	repoRoot := t.TempDir()
	keysDir := filepath.Join(repoRoot, "ops", "keys", "reviewpack")
	os.MkdirAll(keysDir, 0755)

	keyID := "test-key-01"
	pubMeta := CryptoKey{
		KeyID:  keyID,
		Alg:    AlgEd25519,
		PubB64: base64.StdEncoding.EncodeToString(pub),
	}
	// Write JSON
	// We need to marshal it manually or import main? "package main" shares types.
	// But in test, we are in main_test normally or same package.
	// Yes, package main.

	// But `CryptoKey` is in `crypto.go`.
	// We can use it.

	// We need to define `CryptoKey` here or depend on it being in `crypto.go`.
	// Since test is same package, it sees `CryptoKey`.

	// Wait, `json.Marshal`
	// Importing `encoding/json`

	importJSON, _ := json.Marshal(pubMeta)
	os.WriteFile(filepath.Join(keysDir, keyID+".pub"), importJSON, 0644)

	// Test	// Find Key ID
	// Test findKeyID
	// It normally looks for *.pub in keysDir.
	// We wrote keys to tmpDir.
	// Matches `*.pub`.
	// findKeyID now takes keysDir
	// The function expects keysDir.
	// In my refactor: func findKeyID(pub ed25519.PublicKey, keysDir string) (string, error)
	// I need to ensure the test creates keys in the directory `findKeyID` expects.
	// Test creates `filepath.Join(keysDir, keyID+".pub")`.
	// So keysDir should be `keysDir`.

	foundID, err := findKeyID(pub, keysDir)
	if err != nil {
		t.Fatalf("findKeyID failed: %v", err)
	}
	if foundID != keyID {
		t.Errorf("Expected keyID %s, got %s", keyID, foundID)
	}
}
