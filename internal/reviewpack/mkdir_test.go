package reviewpack

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMkdirAllHardeningFailFast(t *testing.T) {
	tmpDir := t.TempDir()
	
	// Create a regular file that will block directory creation
	blocker := filepath.Join(tmpDir, "blocker")
	if err := os.WriteFile(blocker, []byte("I am a file"), 0644); err != nil {
		t.Fatalf("failed to create blocker: %v", err)
	}

	t.Run("ensureDir fails under regular file", func(t *testing.T) {
		target := filepath.Join(blocker, "child")
		err := ensureDir(target)
		if err == nil {
			t.Errorf("expected error from ensureDir, but got nil")
		}
		if !strings.Contains(err.Error(), "mkdir") || !strings.Contains(err.Error(), blocker) {
			t.Errorf("error message should contain 'mkdir' and path, got: %v", err)
		}
	})

	t.Run("generatePlaceholderLog fails if dir blocked", func(t *testing.T) {
		// Attempt to generate log in a directory that is actually a file
		err := generatePlaceholderLog(blocker)
		if err == nil {
			t.Errorf("expected error from generatePlaceholderLog, but got nil")
		}
		t.Logf("Got expected error: %v", err)
	})
}
