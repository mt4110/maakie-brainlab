package reviewpack

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
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

	// S15-09: Forbidden file[:]// URL check
	checkForbiddenFileUrls(repoRoot)
}

func checkForbiddenFileUrls(repoRoot string) {
	log.Printf("DEBUG: Scanning for forbidden %s%s links...", "file", "://")
	files := listTrackedFiles()
	// S15-09: Obfuscate the forbidden pattern in code to avoid self-match correctly.
	// We use string concatenation of runes to avoid literal match.
	pattern := string([]rune{'f', 'i', 'l', 'e', ':', '/', '/'})
	re := regexp.MustCompile(pattern)

	found := false
	for _, rel := range files {
		// S15-09/10 Optimization: Narrow scan to text-like files to avoid binary blobs
		ext := strings.ToLower(filepath.Ext(rel))
		isText := false
		for _, t := range []string{".md", ".go", ".txt", ".patch", ".tsv", ".sh", ".py", ".jsonl", ".json", ".yml", ".yaml", ".toml"} {
			if ext == t {
				isText = true
				break
			}
		}
		if !isText {
			continue
		}

		abs := filepath.Join(repoRoot, rel)
		content, err := os.ReadFile(abs)
		if err != nil {
			log.Fatalf("[FATAL] failed to read tracked file %s: %v", rel, err)
		}
		if re.Match(content) {
			log.Printf("[FAIL] Forbidden %s%s link found in: %s", "file", "://", rel)
			found = true
		}
	}

	if found {
		log.Fatalf("[FATAL] submission aborted: forbidden %s%s links must be removed", "file", "://")
	}
}

func collectGitInfo(repoRoot, packDir, nCommits string) {
	rawDir := filepath.Join(packDir, dirLogsRaw)
	if err := os.MkdirAll(rawDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdir, rawDir, err)
	}
	logPath := filepath.Join(rawDir, fileGitLog)
	runCmd(repoRoot, "git", "log", "-n", nCommits, "--stat", ">", logPath)
	sha10, _ := fileSha256(logPath)
	_ = os.WriteFile(logPath+".sha256", []byte(sha10+"\n"), 0644)

	diffPath := filepath.Join(rawDir, fileGitDiff)
	runCmd(repoRoot, "git", "diff", "HEAD~"+nCommits, "HEAD", ">", diffPath)
	sha11, _ := fileSha256(diffPath)
	_ = os.WriteFile(diffPath+".sha256", []byte(sha11+"\n"), 0644)
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
