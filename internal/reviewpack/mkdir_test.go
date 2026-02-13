package reviewpack

import (
	"os"
	"path/filepath"
	"testing"
)

func TestMkdirAllHardeningFailFast(t *testing.T) {
	tmpDir := t.TempDir()
	
	// Create a regular file that will block directory creation
	blocker := filepath.Join(tmpDir, "blocker")
	if err := os.WriteFile(blocker, []byte("I am a file"), 0644); err != nil {
		t.Fatalf("failed to create blocker: %v", err)
	}

	// Attempt to create a directory at blocker/child
	// This MUST fail on most Unix-like systems
	target := filepath.Join(blocker, "child")
	err := os.MkdirAll(target, 0755)
	
	if err == nil {
		t.Errorf("expected error when creating directory under regular file, but got nil")
	} else {
		t.Logf("Got expected error: %v", err)
	}
}
