package reviewpack

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// TestMkdirFailFastSubprocess verifies that reviewpack actually calls log.Fatalf
// and exits with code 1 when it fails to create a directory.
func TestMkdirFailFastSubprocess(t *testing.T) {
	if os.Getenv("BE_HELPER_PROCESS") == "1" {
		helperProcessMain()
		return
	}

	tmpDir := t.TempDir()
	// Create a regular file that will block directory creation
	blocker := filepath.Join(tmpDir, "blocker")
	if err := os.WriteFile(blocker, []byte("I am a file"), 0644); err != nil {
		t.Fatalf("failed to create blocker: %v", err)
	}

	// We'll try to run setupPackDir with a name that forces it to try creating a dir under 'blocker'
	// Actually setupPackDir uses os.MkdirTemp first, so we might need a different strategy.
	// Let's test a simpler function like copyFile which uses os.MkdirAll(filepath.Dir(dst), 0755)

	target := filepath.Join(blocker, "destination.txt")

	cmd := exec.Command(os.Args[0], "-test.run=TestMkdirFailFastSubprocess")
	cmd.Env = append(os.Environ(), "BE_HELPER_PROCESS=1", "BLOCKER_PATH="+target)

	out, err := cmd.CombinedOutput()

	if err == nil {
		t.Errorf("expected process to fail (exit code 1), but it succeeded. Output:\n%s", string(out))
	}

	exitErr, ok := err.(*exec.ExitError)
	if !ok {
		t.Fatalf("expected *exec.ExitError, got %T: %v", err, err)
	}

	if exitErr.ExitCode() != 1 {
		t.Errorf("expected exit code 1, got %d", exitErr.ExitCode())
	}

	if !strings.Contains(string(out), "[FATAL] mkdir") || !strings.Contains(string(out), blocker) {
		t.Errorf("output should contain '[FATAL] mkdir' and the blocking path. Output:\n%s", string(out))
	}
}

func helperProcessMain() {
	target := os.Getenv("BLOCKER_PATH")
	if target == "" {
		os.Exit(0)
	}

	// Trigger the fail-fast behavior
	// copyFile(src, dst) calls os.MkdirAll(filepath.Dir(dst), 0755)
	// If filepath.Dir(target) is a file, it should fail.
	copyFile("/dev/null", target)

	// Should never reach here because copyFile calls log.Fatalf
	os.Exit(0)
}
