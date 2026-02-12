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
			log.Fatalf(msgFatalMkdirTemp, err)
		}
		defer os.RemoveAll(tmpDir)

		extractTar(target, tmpDir)
		// Assume internal root "review_pack" from S4 spec
		verifyRoot = filepath.Join(tmpDir, "review_pack")
		if _, err := os.Stat(verifyRoot); os.IsNotExist(err) {
			// Fallback: try to find it
			r, err := findDirContainingFile(tmpDir, "PACK_VERSION", 2)
			if err != nil {
				log.Fatalf("[FATAL] Could not find pack root: %v", err)
			}
			verifyRoot = r
		}
	}

	fmt.Printf("=== VERIFY: %s ===\n", verifyRoot)

	// 1. Checksums coverage
	checksumsFile := filepath.Join(verifyRoot, fileChecksums)
	content, err := os.ReadFile(checksumsFile)
	if err != nil {
		log.Fatalf("[FAIL] No CHECKSUMS.sha256 found: %v", err)
	}

	// C10-03: PACK_KIND Check
	if _, err := os.Stat(filepath.Join(verifyRoot, "review_pack_v1")); os.IsNotExist(err) {
		log.Fatalf("[FAIL] Missing PACK_KIND file: review_pack_v1")
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

	// 4. Evidence Marker Check (30_make_test.log)
	testLogPath := filepath.Join(verifyRoot, fileMakeTest)
	logBytes, err := os.ReadFile(testLogPath)
	if err != nil {
		log.Fatalf("[FAIL] Missing test evidence log: %s", fileMakeTest)
	}
	if !bytes.Contains(logBytes, []byte("go test ./...")) {
		log.Fatalf("[FAIL] Evidence missing in %s: 'go test ./...'", fileMakeTest)
	}
	if !bytes.Contains(logBytes, []byte("unittest discover")) {
		log.Fatalf("[FAIL] Evidence missing in %s: 'unittest discover'", fileMakeTest)
	}

	fmt.Println("PASS: Verify OK")
}
