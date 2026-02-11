package main

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const (
	testToolVer = "dev"
)

func TestChainGenesisAndAppend(t *testing.T) {
	dir := t.TempDir()
	w, err := NewChainWriter(dir)
	if err != nil {
		t.Fatalf("NewChainWriter: %v", err)
	}

	// Append first entry (genesis)
	e1 := &ChainEntry{
		TimestampUTC:    "20260211T161122Z",
		PackName:        "review_bundle_001.tar.gz",
		PackSHA256:      "aaaa",
		ManifestSHA256:  "bbbb",
		ChecksumsSHA256: "cccc",
		GitHead:         "abc1234",
		ToolVersion:     testToolVer,
	}
	if err := w.Append(e1); err != nil {
		t.Fatalf("Append 1: %v", err)
	}

	if e1.PrevEntrySHA256 != ChainGenesisHash {
		t.Errorf("first entry prev_hash = %s, want genesis", e1.PrevEntrySHA256)
	}
	if e1.Version != ChainVersion {
		t.Errorf("version = %s, want %s", e1.Version, ChainVersion)
	}

	// Append second entry (chained)
	e2 := &ChainEntry{
		TimestampUTC:    "20260211T161200Z",
		PackName:        "review_bundle_002.tar.gz",
		PackSHA256:      "dddd",
		ManifestSHA256:  "eeee",
		ChecksumsSHA256: "ffff",
		GitHead:         "def5678",
		ToolVersion:     testToolVer,
	}
	if err := w.Append(e2); err != nil {
		t.Fatalf("Append 2: %v", err)
	}

	if e2.PrevEntrySHA256 != e1.EntrySHA256 {
		t.Errorf("second entry prev = %s, want %s", e2.PrevEntrySHA256, e1.EntrySHA256)
	}

	// Validate chain
	chainPath := filepath.Join(dir, ChainDir, ChainFile)
	diags, err := ValidateChain(chainPath)
	if err != nil {
		t.Fatalf("ValidateChain: %v", err)
	}
	if len(diags) > 0 {
		for _, d := range diags {
			t.Errorf("line %d [%s]: %s", d.Line, d.Severity, d.Message)
		}
	}
}

func TestChainTamperDetection(t *testing.T) {
	dir := t.TempDir()
	w, err := NewChainWriter(dir)
	if err != nil {
		t.Fatalf("NewChainWriter: %v", err)
	}

	e := &ChainEntry{
		TimestampUTC:    "20260211T161122Z",
		PackName:        "bundle.tar.gz",
		PackSHA256:      "aaaa",
		ManifestSHA256:  "bbbb",
		ChecksumsSHA256: "cccc",
		GitHead:         "abc1234",
		ToolVersion:     testToolVer,
	}
	if err := w.Append(e); err != nil {
		t.Fatalf("Append: %v", err)
	}

	// Tamper: change pack_name (col 3) in the file
	chainPath := filepath.Join(dir, ChainDir, ChainFile)
	raw, err := os.ReadFile(chainPath)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	tampered := strings.Replace(string(raw), "bundle.tar.gz", "hacked.tar.gz", 1)
	if err := os.WriteFile(chainPath, []byte(tampered), 0644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	diags, err := ValidateChain(chainPath)
	if err != nil {
		t.Fatalf("ValidateChain: %v", err)
	}
	if len(diags) == 0 {
		t.Fatal("expected diagnostics for tampered chain, got none")
	}

	foundHashFail := false
	for _, d := range diags {
		if d.Severity == "FAIL" && strings.Contains(d.Message, "entry_sha256 mismatch") {
			foundHashFail = true
		}
	}
	if !foundHashFail {
		t.Errorf("expected entry_sha256 mismatch diagnostic, got: %v", diags)
	}
}

func TestChainPrevHashMismatch(t *testing.T) {
	dir := t.TempDir()
	w, err := NewChainWriter(dir)
	if err != nil {
		t.Fatalf("NewChainWriter: %v", err)
	}

	e1 := &ChainEntry{
		TimestampUTC: "20260211T161122Z", PackName: "a.tar.gz",
		PackSHA256: "aa", ManifestSHA256: "bb", ChecksumsSHA256: "cc",
		GitHead: "abc", ToolVersion: "dev",
	}
	e2 := &ChainEntry{
		TimestampUTC: "20260211T161200Z", PackName: "b.tar.gz",
		PackSHA256: "dd", ManifestSHA256: "ee", ChecksumsSHA256: "ff",
		GitHead: "def", ToolVersion: "dev",
	}
	w.Append(e1)
	w.Append(e2)

	// Tamper: change prev_entry_sha256 in second line
	chainPath := filepath.Join(dir, ChainDir, ChainFile)
	raw, _ := os.ReadFile(chainPath)
	lines := strings.Split(strings.TrimSpace(string(raw)), "\n")
	cols := strings.Split(lines[1], "\t")
	cols[8] = "deadbeef" // corrupt prev hash
	// Recompute entry hash so only prev_hash is wrong
	payload := strings.Join(cols[:9], "\t")
	sum := sha256.Sum256([]byte(payload))
	cols[9] = hex.EncodeToString(sum[:])
	lines[1] = strings.Join(cols, "\t")
	os.WriteFile(chainPath, []byte(strings.Join(lines, "\n")+"\n"), 0644)

	diags, err := ValidateChain(chainPath)
	if err != nil {
		t.Fatalf("ValidateChain: %v", err)
	}

	foundPrevFail := false
	for _, d := range diags {
		if d.Severity == "FAIL" && strings.Contains(d.Message, "prev_entry_sha256 mismatch") {
			foundPrevFail = true
		}
	}
	if !foundPrevFail {
		t.Errorf("expected prev_entry_sha256 mismatch, got: %v", diags)
	}
}

func TestChainHashComputation(t *testing.T) {
	e := &ChainEntry{
		Version: "1", TimestampUTC: "20260211T161122Z", PackName: "test.tar.gz",
		PackSHA256: "aabb", ManifestSHA256: "ccdd", ChecksumsSHA256: "eeff",
		GitHead: "abc1234", ToolVersion: "dev",
		PrevEntrySHA256: ChainGenesisHash,
	}

	hash := ComputeChainEntryHash(e)

	// Manually compute expected
	payload := "1\t20260211T161122Z\ttest.tar.gz\taabb\tccdd\teeff\tabc1234\tdev\t" + ChainGenesisHash
	expected := sha256.Sum256([]byte(payload))
	expectedHex := hex.EncodeToString(expected[:])

	if hash != expectedHex {
		t.Errorf("hash = %s, want %s", hash, expectedHex)
	}
}

func TestChainParseFormat(t *testing.T) {
	original := &ChainEntry{
		Version: "1", TimestampUTC: "20260211T161122Z",
		PackName: "test.tar.gz", PackSHA256: "aaaa",
		ManifestSHA256: "bbbb", ChecksumsSHA256: "cccc",
		GitHead: "abc", ToolVersion: "dev",
		PrevEntrySHA256: ChainGenesisHash, EntrySHA256: "dddd",
	}

	line := FormatChainEntry(original)
	parsed, err := ParseChainEntry(line)
	if err != nil {
		t.Fatalf("ParseChainEntry: %v", err)
	}

	if parsed.Version != original.Version ||
		parsed.TimestampUTC != original.TimestampUTC ||
		parsed.PackName != original.PackName ||
		parsed.PackSHA256 != original.PackSHA256 ||
		parsed.ManifestSHA256 != original.ManifestSHA256 ||
		parsed.ChecksumsSHA256 != original.ChecksumsSHA256 ||
		parsed.GitHead != original.GitHead ||
		parsed.ToolVersion != original.ToolVersion ||
		parsed.PrevEntrySHA256 != original.PrevEntrySHA256 ||
		parsed.EntrySHA256 != original.EntrySHA256 {
		t.Errorf("round-trip mismatch:\n  original: %+v\n  parsed:   %+v", original, parsed)
	}
}

func TestChainParseInvalidCols(t *testing.T) {
	_, err := ParseChainEntry("too\tfew\tcols")
	if err == nil {
		t.Fatal("expected error for too few columns")
	}
}

func TestChainEmptyFile(t *testing.T) {
	dir := t.TempDir()
	chainDir := filepath.Join(dir, ChainDir)
	os.MkdirAll(chainDir, 0755)
	chainPath := filepath.Join(chainDir, ChainFile)
	os.WriteFile(chainPath, []byte(""), 0644)

	diags, err := ValidateChain(chainPath)
	if err != nil {
		t.Fatalf("ValidateChain: %v", err)
	}
	if len(diags) != 1 || diags[0].Severity != "WARN" {
		t.Errorf("expected 1 WARN for empty chain, got: %v", diags)
	}
}
