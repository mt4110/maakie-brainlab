package reviewpack

import (
	"crypto/sha256"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestVerifyMandatoryLogsSubprocess(t *testing.T) {
	if os.Getenv("BE_HELPER_PROCESS") == "1" {
		helperVerifyProcessMain()
		return
	}

	tests := []struct {
		name         string
		missingFile  string
		expectedFAIL string
	}{
		{
			name:         "missing git log",
			missingFile:  "10_git_log.txt",
			expectedFAIL: "Missing mandatory evidence log: logs/raw/10_git_log.txt",
		},
		{
			name:         "missing self verify",
			missingFile:  "40_self_verify.log",
			expectedFAIL: "Missing mandatory evidence log: logs/raw/40_self_verify.log",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			packDir := filepath.Join(tmpDir, "review_pack")
			rawDir := filepath.Join(packDir, dirLogsRaw)
			_ = os.MkdirAll(rawDir, 0755)

			// Setup standard files
			_ = os.WriteFile(filepath.Join(packDir, filePackVersion), []byte("1\n"), 0644)
			_ = os.WriteFile(filepath.Join(packDir, "review_pack_v1"), []byte("1\n"), 0644)

			var checksumLines []string

			// Helper to add file and checksum
			addFile := func(relPath string, content []byte, mode os.FileMode) {
				p := filepath.Join(packDir, relPath)
				_ = os.MkdirAll(filepath.Dir(p), 0755)
				_ = os.WriteFile(p, content, mode)
				h := sha256.New()
				h.Write(content)
				checksumLines = append(checksumLines, fmt.Sprintf("%x %s", h.Sum(nil), relPath))
			}

			addFile(filePackVersion, []byte("1\n"), 0644)
			addFile("review_pack_v1", []byte("1\n"), 0644)

			logs := []string{"10_git_log.txt", "30_make_test.log", "40_self_verify.log"}
			for _, f := range logs {
				if f == tt.missingFile {
					continue
				}
				rel := filepath.Join(dirLogsRaw, f)

				content := []byte("data")
				if f == "30_make_test.log" {
					content = []byte("+ go test ./...\n+ unittest discover\n")
				}
				addFile(rel, content, 0644)
			}
			_ = os.WriteFile(filepath.Join(packDir, "CHECKSUMS.sha256"), []byte(strings.Join(checksumLines, "\n")+"\n"), 0644)

			cmd := exec.Command(os.Args[0], "-test.run=TestVerifyMandatoryLogsSubprocess")
			cmd.Env = append(os.Environ(), "BE_HELPER_PROCESS=1", "VERIFY_ROOT="+packDir)
			out, err := cmd.CombinedOutput()

			if err == nil {
				t.Errorf("expected failure for %s, but succeeded. Output:\n%s", tt.name, string(out))
			}
			if !strings.Contains(string(out), "[FAIL]") || !strings.Contains(string(out), tt.expectedFAIL) {
				t.Errorf("expected output to contain %q. Output:\n%s", tt.expectedFAIL, string(out))
			}
		})
	}
}

func helperVerifyProcessMain() {
	root := os.Getenv("VERIFY_ROOT")
	if root == "" {
		return
	}
	runVerify([]string{root})
	os.Exit(0)
}
