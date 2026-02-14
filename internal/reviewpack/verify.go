package reviewpack

import (
	"bufio"
	"bytes"
	"fmt"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func runVerify(args []string) {
	if len(args) < 1 {
		log.Fatal("Usage: reviewpack verify <dir|tar.gz>")
	}
	target := args[0]

	verifyRoot := target
	if strings.HasSuffix(target, ".tar.gz") {
		tmpDir, err := os.MkdirTemp("", "reviewpack-verify-*")
		if err != nil {
			log.Fatalf(msgFatalMkdirTemp, "reviewpack-verify-*", err)
		}
		defer os.RemoveAll(tmpDir)

		extractTar(target, tmpDir)
		// Assume internal root "review_pack" from S4 spec
		verifyRoot = filepath.Join(tmpDir, "review_pack")
		if _, err := os.Stat(verifyRoot); os.IsNotExist(err) {
			// Fallback: try to find it
			r, err := findDirContainingFile(tmpDir, "PACK_VERSION", 2)
			if err != nil {
				log.Fatalf("[FATAL] Could not find pack root in %s: %v", tmpDir, err)
			}
			verifyRoot = r
		}
	}

	fmt.Printf("=== VERIFY: %s ===\n", verifyRoot)

	// 1. Checksums coverage
	checksumsFile := filepath.Join(verifyRoot, fileChecksums)
	content, err := os.ReadFile(checksumsFile)
	if err != nil {
		log.Fatalf("[FAIL] No %s found: %v", checksumsFile, err)
	}

	// C10-03: PACK_KIND Check
	packKindFile := filepath.Join(verifyRoot, "review_pack_v1")
	if _, err := os.Stat(packKindFile); os.IsNotExist(err) {
		log.Fatalf("[FAIL] Missing PACK_KIND file: %s", packKindFile)
	}

	validFiles := make(map[string]bool)
	scanner := bufio.NewScanner(bytes.NewReader(content))
	for scanner.Scan() {
		parts := strings.Fields(scanner.Text())
		if len(parts) != 2 {
			continue
		}
		relPath := parts[1]
		validFiles[relPath] = true

		absPath := filepath.Join(verifyRoot, relPath)
		hash, err := fileSha256(absPath)
		if err != nil {
			log.Printf("[FAIL] missing or unreadable: %s", relPath)
			os.Exit(1)
		}
		if hash != parts[0] {
			log.Printf("[FAIL] checksum mismatch: %s", relPath)
			os.Exit(1)
		}
		fmt.Printf("[OK] %s\n", relPath)
	}

	// 2. Strict check for extra files
	var extraFiles []string
	err = filepath.WalkDir(verifyRoot, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		relPath, err := filepath.Rel(verifyRoot, path)
		if err != nil {
			return err
		}
		if relPath == fileChecksums {
			return nil
		}
		if _, ok := validFiles[relPath]; !ok {
			extraFiles = append(extraFiles, relPath)
		}
		return nil
	})
	if err != nil {
		log.Fatalf("[FATAL] walk directory: %v", err)
	}

	if len(extraFiles) > 0 {
		fmt.Printf("[FAIL] Extra files found in pack:\n")
		sort.Strings(extraFiles)
		for _, f := range extraFiles {
			fmt.Printf("  - %s\n", f)
		}
		os.Exit(1)
	}

	// 4. Evidence Marker Check (logs/raw/30_make_test.log + others)
	// S15-10 Hardening: check for mandatory logs
	for _, f := range []string{fileGitLog, fileMakeTest, fileSelfVerify} {
		p := filepath.Join(verifyRoot, dirLogsRaw, f)
		if _, err := os.Stat(p); os.IsNotExist(err) {
			log.Fatalf("[FAIL] Missing mandatory evidence log: %s/%s", dirLogsRaw, f)
		}
	}

	testLogPath := filepath.Join(verifyRoot, dirLogsRaw, fileMakeTest)
	logBytes, err := os.ReadFile(testLogPath)
	if err != nil {
		log.Fatalf("[FAIL] Could not read test evidence log: %s/%s", dirLogsRaw, fileMakeTest)
	}

	hasGoTest := false
	hasUnittest := false

	evScanner := bufio.NewScanner(bytes.NewReader(logBytes))
	// S8 Hotfix: Handle long lines (e.g. 1MB buffer) and check for errors
	buf := make([]byte, 1024*1024)
	evScanner.Buffer(buf, 1024*1024)

	for evScanner.Scan() {
		line := strings.TrimSpace(evScanner.Text())
		// Strip shell execution markers if present
		line = strings.TrimPrefix(line, "+ ")

		if strings.HasPrefix(line, "go test") && strings.Contains(line, "./...") {
			hasGoTest = true
		}
		if strings.HasPrefix(line, "unittest discover") || strings.Contains(line, "python -m unittest discover") {
			hasUnittest = true
		}
	}

	if err := evScanner.Err(); err != nil {
		log.Fatalf("[FATAL] Error scanning evidence log %s/%s: %v", dirLogsRaw, fileMakeTest, err)
	}

	if !hasGoTest {
		log.Fatalf("[FAIL] Evidence missing in %s/%s: 'go test ./...' (required for Audit Tightening/Strict mode)", dirLogsRaw, fileMakeTest)
	}
	if !hasUnittest {
		log.Fatalf("[FAIL] Evidence missing in %s/%s: 'unittest discover'", dirLogsRaw, fileMakeTest)
	}

	fmt.Println("PASS: Verify OK")
}
