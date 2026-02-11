package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestListKinds(t *testing.T) {
	tmpDir := t.TempDir()
	packsDir := filepath.Join(tmpDir, "packs")

	// 1. Empty case
	kinds, err := listKinds(tmpDir)
	if err != nil {
		t.Fatalf("listKinds failed: %v", err)
	}
	if len(kinds) != 0 {
		t.Errorf("expected 0 kinds, got %d", len(kinds))
	}

	// 2. Populated case
	os.MkdirAll(filepath.Join(packsDir, "b_kind"), 0755)
	os.MkdirAll(filepath.Join(packsDir, "a_kind"), 0755)
	os.WriteFile(filepath.Join(packsDir, "not_a_dir"), []byte("data"), 0644)

	kinds, err = listKinds(tmpDir)
	if err != nil {
		t.Fatalf("listKinds failed: %v", err)
	}

	if len(kinds) != 2 {
		t.Fatalf("expected 2 kinds, got %d", len(kinds))
	}
	if kinds[0] != "a_kind" || kinds[1] != "b_kind" {
		t.Errorf("expected [a_kind, b_kind] (sorted), got %v", kinds)
	}
}

func TestRunKindsSubcommand(t *testing.T) {
	tmpDir := t.TempDir()
	packsDir := filepath.Join(tmpDir, "packs")
	os.MkdirAll(filepath.Join(packsDir, "test_kind"), 0755)

	// Capture output or just check for lack of errors
	err := runKinds([]string{"--store", tmpDir})
	if err != nil {
		t.Errorf("runKinds failed: %v", err)
	}
}
