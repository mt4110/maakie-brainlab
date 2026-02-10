package reviewpack

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

// resolveRepoRoot ensures we are inside the repo and returns the root path.
func resolveRepoRoot() string {
	// Try Getwd first
	if _, err := os.Getwd(); err != nil {
		log.Fatalf("[FATAL] Getwd: %v", err)
	}

	out, err := exec.Command("git", "rev-parse", "--show-toplevel").Output()
	if err != nil {
		log.Fatalf("[FATAL] git rev-parse --show-toplevel failed: %v", err)
	}
	root := strings.TrimSpace(string(out))
	if root == "" {
		log.Fatalf("[FATAL] git rev-parse --show-toplevel returned empty")
	}
	if err := os.Chdir(root); err != nil {
		log.Fatalf("[FATAL] chdir to repo root failed: %v", err)
	}
	return root
}

func listTrackedFiles() []string {
	out, err := exec.Command("git", "ls-files").Output()
	if err != nil {
		log.Fatalf("[FATAL] git ls-files: %v", err)
	}
	var files []string
	scanner := bufio.NewScanner(bytes.NewReader(out))
	for scanner.Scan() {
		f := strings.TrimSpace(scanner.Text())
		if f == "" {
			continue
		}
		files = append(files, f)
	}
	sort.Strings(files)
	return files
}

// findLatestEvalResult scans for the latest timestamped jsonl in eval/results (ignoring latest.jsonl).
func findLatestEvalResult(repoRoot string) (string, string, error) {
	resultsDir := filepath.Join(repoRoot, dirEvalResults)
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		return "", "", fmt.Errorf("read %s: %w", resultsDir, err)
	}

	var candidates []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		if name == "latest.jsonl" {
			continue
		}
		if strings.HasSuffix(name, ".jsonl") {
			candidates = append(candidates, name)
		}
	}

	if len(candidates) == 0 {
		return "", "", fmt.Errorf("no .jsonl files found in %s (excluding latest.jsonl)", resultsDir)
	}

	// Sort by name (timestamp assumption: YYYYMMDD-HHMMSS...)
	sort.Strings(candidates)
	latest := candidates[len(candidates)-1]

	absPath := filepath.Join(resultsDir, latest)
	relPath := filepath.Join("eval/results", latest)
	return absPath, relPath, nil
}

// validateJsonlLooksOk checks if file exists, size > 0, and starts with '{'.
func validateJsonlLooksOk(absPath string) error {
	fi, err := os.Stat(absPath)
	if err != nil {
		return err
	}
	if fi.Size() == 0 {
		return fmt.Errorf("file is empty")
	}

	f, err := os.Open(absPath)
	if err != nil {
		return err
	}
	defer func() { _ = f.Close() }()

	scanner := bufio.NewScanner(f)
	if scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if !strings.HasPrefix(line, "{") {
			return fmt.Errorf("first line does not start with '{'")
		}
	} else {
		if err := scanner.Err(); err != nil {
			return err
		}
		return fmt.Errorf("file has no content to scan")
	}
	return nil
}

// copyEvalAsLatest copies the source jsonl to snapshot/eval/results/latest.jsonl
// and returns its sha256 and bytes.
func copyEvalAsLatest(snapshotDir, srcAbs string) (string, int64, string, error) {
	dstRel := "eval/results/latest.jsonl"
	dstAbs := filepath.Join(snapshotDir, dstRel)

	if err := os.MkdirAll(filepath.Dir(dstAbs), 0755); err != nil {
		return "", 0, "", fmt.Errorf("mkdir %s: %w", filepath.Dir(dstAbs), err)
	}

	// Copy
	srcF, err := os.Open(srcAbs)
	if err != nil {
		return "", 0, "", fmt.Errorf("open src %s: %w", srcAbs, err)
	}
	defer func() { _ = srcF.Close() }()

	dstF, err := os.Create(dstAbs)
	if err != nil {
		return "", 0, "", fmt.Errorf("create dst %s: %w", dstAbs, err)
	}
	defer func() { _ = dstF.Close() }() // Proper close handling in loop if needed, but here simple

	// TeeReader to calc sha256 while copying? Or just copy then calc?
	// Let's copy then calc to match existing patterns (fileSha256) or do it here efficiently.
	// Since we need to return sha/bytes, let's do it here.
	hasher := sha256.New()
	multi := io.MultiWriter(dstF, hasher)

	copied, err := io.Copy(multi, srcF)
	if err != nil {
		return "", 0, "", fmt.Errorf("copy failed: %w", err)
	}

	return fmt.Sprintf("%x", hasher.Sum(nil)), copied, dstAbs, nil
}
