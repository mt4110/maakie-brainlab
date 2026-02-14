package reviewpack

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFindLatestEvalResult(t *testing.T) {
	tmpDir := t.TempDir()
	resultsDir := filepath.Join(tmpDir, dirEvalResults)
	if err := os.MkdirAll(resultsDir, 0755); err != nil {
		t.Fatalf("failed to create results dir: %v", err)
	}

	// 1. empty
	_, _, err := findLatestEvalResult(tmpDir)
	if err == nil {
		t.Error("expected error for empty results dir, got nil")
	}

	// 2. newest is valid
	v1 := filepath.Join(resultsDir, "20231001-120000.jsonl")
	v2 := filepath.Join(resultsDir, "20231002-120000.jsonl")
	validContent := `{"id":1}` + "\n"
	_ = os.WriteFile(v1, []byte(validContent), 0644)
	_ = os.WriteFile(v2, []byte(validContent), 0644)

	abs, _, err := findLatestEvalResult(tmpDir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if filepath.Base(abs) != "20231002-120000.jsonl" {
		t.Errorf("expected 20231002-120000.jsonl, got %s", filepath.Base(abs))
	}

	// 3. newest is invalid (staleness check)
	v3 := filepath.Join(resultsDir, "20231003-120000.jsonl")
	invalidContent := `invalid` + "\n"
	_ = os.WriteFile(v3, []byte(invalidContent), 0644)

	_, _, err = findLatestEvalResult(tmpDir)
	if err == nil {
		t.Error("expected error because newest result is invalid, but got nil (silent fallback check)")
	}
}
