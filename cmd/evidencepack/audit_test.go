package main

import (
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const testTimestamp = "2024-01-01T00:00:00Z"

// ---------------------------------------------------------------------------
// TestAuditLogHashChain — verifies AuditLogger writes connected hash entries
// ---------------------------------------------------------------------------

func TestAuditLogHashChain(t *testing.T) {
	tmpDir := t.TempDir()

	logger, err := NewAuditLogger(tmpDir)
	if err != nil {
		t.Fatalf("Failed to init logger: %v", err)
	}

	e1 := &AuditEntry{EventType: "test", Result: "ok", ArtifactSHA256: "aaa", UTCTimestamp: testTimestamp}
	if err := logger.LogEvent(e1); err != nil {
		t.Fatalf("LogEvent 1 failed: %v", err)
	}

	e2 := &AuditEntry{EventType: "test", Result: "fail", ArtifactSHA256: "bbb", UTCTimestamp: "2024-01-01T00:00:01Z"}
	if err := logger.LogEvent(e2); err != nil {
		t.Fatalf("LogEvent 2 failed: %v", err)
	}

	content, err := os.ReadFile(logger.path)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	logLines := strings.Split(strings.TrimSpace(string(content)), "\n")
	if len(logLines) != 2 {
		t.Fatalf("Expected 2 lines, got %d", len(logLines))
	}

	var entry1, entry2 AuditEntry
	json.Unmarshal([]byte(logLines[0]), &entry1)
	json.Unmarshal([]byte(logLines[1]), &entry2)

	if entry1.PrevHash != GenesisHash {
		t.Errorf("Entry1 PrevHash expected %s, got %s", GenesisHash, entry1.PrevHash)
	}
	if entry1.EntryHash == "" {
		t.Error("Entry1 EntryHash is empty")
	}
	if entry2.PrevHash != entry1.EntryHash {
		t.Errorf("Chain broken: Entry2.PrevHash %s != Entry1.EntryHash %s", entry2.PrevHash, entry1.EntryHash)
	}
}

// ---------------------------------------------------------------------------
// TestCanonicalAuditJSON — deterministic output
// ---------------------------------------------------------------------------

func TestCanonicalAuditJSON(t *testing.T) {
	e := &AuditEntry{
		EventType:      "sign",
		Result:         "ok",
		ArtifactPath:   "/path/to/artifact",
		ArtifactSHA256: "abc123",
		UTCTimestamp:   "2024-01-01T00:00:00Z",
		PrevHash:       GenesisHash,
		EntryHash:      "should_be_excluded",
	}

	b1, err := CanonicalAuditJSON(e)
	if err != nil {
		t.Fatal(err)
	}
	b2, err := CanonicalAuditJSON(e)
	if err != nil {
		t.Fatal(err)
	}

	if string(b1) != string(b2) {
		t.Errorf("canonical JSON is not deterministic:\n%s\n!=\n%s", b1, b2)
	}

	// entry_hash must be "" in canonical output
	if strings.Contains(string(b1), "should_be_excluded") {
		t.Error("canonical JSON contains entry_hash value; it must be empty")
	}
	if !strings.Contains(string(b1), `"entry_hash":""`) {
		t.Error("canonical JSON missing empty entry_hash field")
	}
}

// ---------------------------------------------------------------------------
// TestVerifyBundleAlsoVerifiesAudit_WhenPresent
// ---------------------------------------------------------------------------

func TestVerifyBundleAlsoVerifiesAuditWhenPresent(t *testing.T) {
	t.Setenv(EnvPolicyMode, "local")
	tmp := t.TempDir()
	storeDir := filepath.Join(tmp, "store")
	payloadDir := filepath.Join(tmp, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, "file.txt"), []byte("data"), 0644)

	// Create TSV chain (S10-00 requirement)
	// AuditLogger is only for event logs (jsonl), not the chain itself.
	// runBundle now looks for ChainFile (.local/reviewpack_artifacts/AUDIT_CHAIN_v1.tsv)
	// So we must create that.
	chainWriter, err := NewChainWriter(tmp)
	if err != nil {
		t.Fatal(err)
	}
	chainWriter.Append(&ChainEntry{
		TimestampUTC: "20260211T161122Z", PackName: "pack.tar.gz",
		PackSHA256: "aa", ManifestSHA256: "bb", ChecksumsSHA256: "cc",
		GitHead: "abc", ToolVersion: "dev",
	})

	// Pack artifact
	if err := runPack([]string{"--kind", "auditbundle", "--store", storeDir, payloadDir}); err != nil {
		t.Fatalf("runPack failed: %v", err)
	}

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "auditbundle"))
	artifactPath := filepath.Join(storeDir, "packs", "auditbundle", entries[0].Name())

	// Create policy
	policyFile := filepath.Join(tmp, "policy.toml")
	os.WriteFile(policyFile, []byte("version=1\n[enforcement]\nlocal='permissive'\n"), 0644)

	// NewChainWriter(tmp) writes chain files under tmp/.local/reviewpack_artifacts,
	// so --audit-dir must point to that directory.
	auditDir := filepath.Join(tmp, ChainDir)

	bundlePath := filepath.Join(tmp, "bundle.tar.gz")
	err = runBundle([]string{
		"--artifact", artifactPath,
		"--policy", policyFile,
		"--out", bundlePath,
		"--audit-dir", auditDir,
	})
	if err != nil {
		t.Fatalf("runBundle failed: %v", err)
	}

	// Verify bundle — should pass (valid audit chain inside)
	if err := verifyPack(VerifyConfig{Path: bundlePath, RepoRoot: ".", PolicyMode: "local"}); err != nil {
		t.Fatalf("verifyPack failed on bundle with valid audit: %v", err)
	}

	// Now tamper the audit inside the bundle
	tamperBundleAudit(t, bundlePath)

	// Verify again — should fail
	err = verifyPack(VerifyConfig{Path: bundlePath, RepoRoot: ".", PolicyMode: "local"})
	if err == nil {
		t.Fatal("Expected verifyPack to fail on tampered audit, but it passed")
	}
	// Check for typed error
	if ve, ok := err.(*VerifyError); ok {
		if ve.Code != ExitTamper {
			t.Errorf("Expected ExitTamper (%d), got %d", ExitTamper, ve.Code)
		}
	} else {
		t.Errorf("Expected VerifyError, got %T: %v", err, err)
	}
}

// ---------------------------------------------------------------------------
// TestVerifyBundlePassesWithoutAudit
// ---------------------------------------------------------------------------

func TestVerifyBundlePassesWithoutAudit(t *testing.T) {
	t.Setenv(EnvPolicyMode, "local")
	tmp := t.TempDir()
	storeDir := filepath.Join(tmp, "store")
	payloadDir := filepath.Join(tmp, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, "file.txt"), []byte("data"), 0644)

	if err := runPack([]string{"--kind", "noaudit", "--store", storeDir, payloadDir}); err != nil {
		t.Fatalf("runPack failed: %v", err)
	}

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "noaudit"))
	artifactPath := filepath.Join(storeDir, "packs", "noaudit", entries[0].Name())

	policyFile := filepath.Join(tmp, "policy.toml")
	os.WriteFile(policyFile, []byte("version=1\n[enforcement]\nlocal='permissive'\n"), 0644)

	bundlePath := filepath.Join(tmp, "bundle.tar.gz")
	err := runBundle([]string{
		"--artifact", artifactPath,
		"--policy", policyFile,
		"--out", bundlePath,
	})
	if err != nil {
		t.Fatalf("runBundle failed: %v", err)
	}

	// No audit dir was specified, so bundle has no audit — should pass
	if err := verifyPack(VerifyConfig{Path: bundlePath, RepoRoot: ".", PolicyMode: "local"}); err != nil {
		t.Fatalf("verifyPack failed on bundle without audit: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Helper: tamper audit inside a bundle tar.gz
// ---------------------------------------------------------------------------

func tamperBundleAudit(t *testing.T, bundlePath string) {
	t.Helper()

	// Two-pass approach: tamper audit content, then update manifest hash.
	tamperedContent := tamperFirstAuditEntry(t, bundlePath)
	updateManifestHash(t, bundlePath, tamperedContent)
}

func tamperFirstAuditEntry(t *testing.T, bundlePath string) []byte {
	t.Helper()
	var result []byte
	modifyTar(t, bundlePath, func(name string, content []byte) []byte {
		if !strings.Contains(name, ChainFile) {
			return content
		}
		// Tamper TSV: change last column (hash)
		lines := strings.Split(strings.TrimSpace(string(content)), "\n")
		if len(lines) == 0 {
			return content
		}
		cols := strings.Split(lines[0], "\t")
		if len(cols) > 0 {
			cols[len(cols)-1] = "badhash" // Tamper entry_sha256
		}
		lines[0] = strings.Join(cols, "\t")

		result = []byte(strings.Join(lines, "\n") + "\n")
		return result
	}, nil)
	if result == nil {
		t.Fatal("audit chain file not found in bundle tar")
	}
	return result
}

func updateManifestHash(t *testing.T, bundlePath string, tamperedContent []byte) {
	t.Helper()
	newHash := sha256Bytes(tamperedContent)
	modifyTar(t, bundlePath, func(name string, content []byte) []byte {
		if !strings.Contains(name, "BUNDLE_MANIFEST.tsv") {
			return content
		}
		lines := strings.Split(strings.TrimSpace(string(content)), "\n")
		for i, line := range lines {
			if !strings.Contains(line, "audit/"+ChainFile) {
				continue
			}
			parts := strings.SplitN(line, "\t", 2)
			if len(parts) == 2 {
				lines[i] = hex.EncodeToString(newHash) + "\t" + parts[1]
			}
		}
		return []byte(strings.Join(lines, "\n") + "\n")
	}, nil)
}
