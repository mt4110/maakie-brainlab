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

func runPreflightChecks(repoRoot, packDir, timestamp string, timebox int, skipEval bool, mode string, skipTest bool) {
	log.Println(msgDebugPreflight)
	// Write pending meta (pass 0/empty for results as they are unknown yet)
	writeMeta(packDir, timestamp, timebox, skipEval, mode, skipTest, "", 0, "", "", 0)

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

	// S15-09: Forbidden file:// URL check
	checkForbiddenFileUrls(repoRoot)
}

func checkForbiddenFileUrls(repoRoot string) {
	log.Println("DEBUG: Scanning for forbidden file:// links...")
	files := listTrackedFiles()
	// Forbidden pattern: "file" + ":" + "//"
	pattern := `file` + `:` + `//`
	re := regexp.MustCompile(pattern)

	found := false
	for _, rel := range files {
		// Skip binary files or large files if needed, but for docs it's fast
		abs := filepath.Join(repoRoot, rel)
		content, err := os.ReadFile(abs)
		if err != nil {
			continue
		}
		if re.Match(content) {
			log.Printf("[FAIL] Forbidden file:// link found in: %s", rel)
			found = true
		}
	}

	if found {
		log.Fatalf("[FATAL] submission aborted: forbidden file:// links must be removed")
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
	fmt.Printf("[INFO] naive secrets scan report:\n%s", buf.String())
}

func scanNull(dir string, data []byte) {
	if bytes.Contains(data, []byte{0}) {
		fmt.Println("[WARN] naive scan: NUL bytes detected in staged diff")
	}
}
