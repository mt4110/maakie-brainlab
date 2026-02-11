package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const (
	healthTestPack1 = "a.tar.gz"
	healthTestPack2 = "b.tar.gz"
)

func TestHealthOK(t *testing.T) {
	dir := t.TempDir()
	w, err := NewChainWriter(dir)
	if err != nil {
		t.Fatalf("NewChainWriter: %v", err)
	}

	w.Append(&ChainEntry{
		TimestampUTC: "20260211T161122Z", PackName: healthTestPack1,
		PackSHA256: "aa", ManifestSHA256: "bb", ChecksumsSHA256: "cc",
		GitHead: "abc", ToolVersion: "dev",
	})
	w.Append(&ChainEntry{
		TimestampUTC: "20260211T161200Z", PackName: healthTestPack2,
		PackSHA256: "dd", ManifestSHA256: "ee", ChecksumsSHA256: "ff",
		GitHead: "def", ToolVersion: "dev",
	})

	chainPath := filepath.Join(dir, ChainDir, ChainFile)
	err = runHealthCheck(chainPath)
	if err != nil {
		t.Errorf("expected nil error for healthy chain, got: %v", err)
	}
}

func TestHealthBrokenChain(t *testing.T) {
	dir := t.TempDir()
	w, _ := NewChainWriter(dir)

	w.Append(&ChainEntry{
		TimestampUTC: "20260211T161122Z", PackName: healthTestPack1,
		PackSHA256: "aa", ManifestSHA256: "bb", ChecksumsSHA256: "cc",
		GitHead: "abc", ToolVersion: "dev",
	})

	// Tamper
	chainPath := filepath.Join(dir, ChainDir, ChainFile)
	raw, _ := os.ReadFile(chainPath)
	tampered := strings.Replace(string(raw), "a.tar.gz", "hacked.tar.gz", 1)
	os.WriteFile(chainPath, []byte(tampered), 0644)

	err := runHealthCheck(chainPath)
	if err == nil {
		t.Fatal("expected error for broken chain")
	}

	he, ok := err.(*HealthError)
	if !ok {
		t.Fatalf("expected HealthError, got %T", err)
	}
	if he.Code != ExitTamper {
		t.Errorf("exit code = %d, want %d", he.Code, ExitTamper)
	}
}

func TestHealthMissingFile(t *testing.T) {
	dir := t.TempDir()
	chainPath := filepath.Join(dir, "nonexistent", ChainFile)

	err := runHealthCheck(chainPath)
	if err != nil {
		t.Errorf("missing chain should be a WARN (nil error), got: %v", err)
	}
}
