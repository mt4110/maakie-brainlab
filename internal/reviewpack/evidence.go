package reviewpack

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
)

func runPreflightChecks(repoRoot, packDir, timestamp string, timebox int, skipEval bool, mode string) {
	log.Println(msgDebugPreflight)
	// Write pending meta (pass 0/empty for results as they are unknown yet)
	writeMeta(packDir, timestamp, timebox, skipEval, mode, "", 0, "", "", 0)

	runCmd(repoRoot, "git", "status", ">", filepath.Join(packDir, fileStatus))

	// Strict clean check
	log.Println("DEBUG: Checking git status --porcelain...")
	cmd := exec.Command("git", "status", "--porcelain")
	cmd.Dir = repoRoot
	porcelainOut, err := cmd.Output()
	if err != nil {
		log.Fatalf(msgFatalGitStatus, err)
	}
	if len(bytes.TrimSpace(porcelainOut)) > 0 {
		log.Printf("[FATAL] preflight: working tree is dirty:\n%s", string(porcelainOut))
		os.Exit(1)
	}
}

func collectGitInfo(repoRoot, packDir, nCommits string) {
	runCmd(repoRoot, "git", "log", "-n", nCommits, "--stat", ">", filepath.Join(packDir, fileGitLog))
	runCmd(repoRoot, "git", "diff", "HEAD~"+nCommits, "HEAD", ">", filepath.Join(packDir, fileGitDiff))
}

func scanSecrets(dir string) {
	// Replaced by strict contamination checks in generatePackFilelist
	// Keeping this signature/call for naive scan if enabled, otherwise no-op or just report
	// We'll keep it as a 'naive scan' report generator for now, but not the enforcer.
	outPath := filepath.Join(dir, "21_secrets_scan.txt")
	var buf bytes.Buffer
	buf.WriteString("secret scan: naive patterns\n")

	diff, _ := exec.Command("git", "diff", "--cached").Output()
	combined := diff

	scanNull(dir, combined)
	re := regexp.MustCompile(`sk-[A-Za-z0-9]{20,}`)
	matches := re.FindAll(combined, -1)
	if len(matches) > 0 {
		buf.WriteString(fmt.Sprintf("FOUND %d potential secrets\n", len(matches)))
	} else {
		buf.WriteString("OK: no obvious secrets\n")
	}
	if err := os.WriteFile(outPath, buf.Bytes(), 0644); err != nil {
		log.Fatalf("[FATAL] write secrets scan: %v", err)
	}
}

func scanNull(dir string, data []byte) {
	if bytes.Contains(data, []byte{0}) {
		_ = os.WriteFile(filepath.Join(dir, "20_null_bytes.txt"), []byte("NUL bytes detected\n"), 0644)
	}
}
