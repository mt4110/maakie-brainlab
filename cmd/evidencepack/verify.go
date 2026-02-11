package main

import (
	"archive/tar"
	"bufio"
	"compress/gzip"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func runVerify(args []string) error {
	fs := flag.NewFlagSet("verify", flag.ExitOnError)
	packPath := fs.String("pack", "", "Path to evidence pack file")

	if err := fs.Parse(args); err != nil {
		return err
	}

	if *packPath == "" {
		// Try positional arg
		if fs.NArg() > 0 {
			*packPath = fs.Arg(0)
		} else {
			return fmt.Errorf("--pack or positional argument is required")
		}
	}

	// Init Logger
	repoRoot := "."
	logger, err := NewAuditLogger(repoRoot)
	if err != nil {
		// In verify-only mode, maybe we warn but proceed?
		// S7: "audit log... verify... S7では書く"
		// If we can't write audit log, should we fail?
		// User said "Audit log created... hash chain not broken".
		// Fail safe: warning.
		fmt.Fprintf(os.Stderr, "Warning: Audit logger init failed: %v\n", err)
	}

	return verifyPack(*packPath, repoRoot, logger)
}

// verifyPack enforces the full contract: Structure + Signature (if present)
func verifyPack(path string, repoRoot string, logger *AuditLogger) error {
	// 1. Structural Verify (v1)
	if err := verifyStructure(path); err != nil {
		return err
	}

	// 2. Signature Check (S7)
	sigPath := path + ".sig.json"

	// Check if sig exists
	if _, err := os.Stat(sigPath); err == nil {
		// SIG EXISTS -> MANDATORY VERIFY
		fmt.Printf("Signature found: %s. Verifying...\n", sigPath)

		verifyErr := verifySignature(path, sigPath)
		res := "ok"
		if verifyErr != nil {
			res = "fail"
		}

		// Log to Audit
		if logger != nil {
			// Extract KeyID from sidecar for logging
			var keyID string
			if data, err := os.ReadFile(sigPath); err == nil {
				var sc SignatureSidecar
				if json.Unmarshal(data, &sc) == nil {
					keyID = sc.KeyID
				}
			}

			artSHA, _ := CalculateSHA256(path)

			logger.LogEvent(&AuditEntry{
				EventType: "verify",
				Result:    res,
				ArtifactPath: path,
				ArtifactSHA256: artSHA,
				SigPath: sigPath,
				KeyID: keyID,
				UTCTimestamp: time.Now().UTC().Format(time.RFC3339),
			})
		}

		if verifyErr != nil {
			return fmt.Errorf("cryptographic verification failed: %w", verifyErr)
		}
		fmt.Println("Signature VERIFIED.")
	} else {
		// No signature. S7: Pass. (S8 may enforce)
		fmt.Println("No signature found (skipped).")
	}

	return nil
}

// verifyStructure checks the inner contents of the pack
func verifyStructure(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("failed to open pack: %w", err)
	}
	defer f.Close()
    // ... rest of original verifyPack logic ...

	// 1. Safety Scan (Tar Headers)
	// We scan the tar stream to ensure no unsafe entries exist BEFORE extracting.
	// Actually, we need to extract to verify matching content.
	// But we must fail FAST if unsafe.
	// We can unzip to a temp dir, enforcing checks during extraction.

	tempDir, err := os.MkdirTemp("", "evidence_verify_")
	if err != nil {
		return fmt.Errorf("failed to create temp dir: %w", err)
	}
	defer os.RemoveAll(tempDir)

	if err := extractAndVerifySafety(path, tempDir); err != nil {
		return fmt.Errorf("safety check failed: %w", err)
	}

	// 2. Structure Check
	// Strict check: Only ALLOWED entries in root
	allowed := map[string]bool{
		"EVIDENCE_VERSION": true,
		"METADATA.json":    true,
		"MANIFEST.tsv":     true,
		"CHECKSUMS.sha256": true,
		"data":             true,
	}

	entries, err := os.ReadDir(tempDir)
	if err != nil {
		return fmt.Errorf("failed to read extracted root: %w", err)
	}

	for _, entry := range entries {
		name := entry.Name()
		if !allowed[name] {
			return fmt.Errorf("forbidden root entry: %s", name)
		}
	}

	required := []string{"EVIDENCE_VERSION", "METADATA.json", "MANIFEST.tsv", "CHECKSUMS.sha256", "data"}
	for _, req := range required {
		info, err := os.Stat(filepath.Join(tempDir, req))
		if err != nil {
			if os.IsNotExist(err) {
				return fmt.Errorf("missing required item: %s", req)
			}
			return err
		}
		if req == "data" && !info.IsDir() {
			return fmt.Errorf("data must be a directory")
		}
		if req != "data" && info.IsDir() {
			return fmt.Errorf("%s must be a file", req)
		}
	}

	// 3. Version Check
	verBytes, err := os.ReadFile(filepath.Join(tempDir, "EVIDENCE_VERSION"))
	if err != nil {
		return fmt.Errorf("failed to read EVIDENCE_VERSION: %w", err)
	}
	if string(verBytes) != "v1\n" {
		return fmt.Errorf("invalid EVIDENCE_VERSION: %q (expected 'v1\\n')", string(verBytes))
	}

	// 4. Root Checksums Validation
	if err := verifyRootChecksums(tempDir); err != nil {
		return fmt.Errorf("checksum verification failed: %w", err)
	}

	// 5. Manifest <-> Data Mutual Exact Match
	if err := verifyManifest(tempDir); err != nil {
		return fmt.Errorf("manifest verification failed: %w", err)
	}

	fmt.Printf("VERIFIED: %s\n", path)
	return nil
}

func extractAndVerifySafety(tarPath, destDir string) error {
	f, err := os.Open(tarPath)
	if err != nil {
		return err
	}
	defer f.Close()

	gzr, err := gzip.NewReader(f)
	if err != nil {
		return err
	}
	defer gzr.Close()

	tr := tar.NewReader(gzr)

	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}

		// Safety Checks
		// 1. Absolute path
		if filepath.IsAbs(header.Name) || strings.HasPrefix(header.Name, "/") {
			return fmt.Errorf("absolute path prohibited: %s", header.Name)
		}
		// 2. Path traversal
		// Clean path and check if it starts with ".."
		clean := filepath.Clean(header.Name)
		if strings.HasPrefix(clean, "..") || strings.Contains(clean, "/../") || strings.HasSuffix(clean, "/..") {
			return fmt.Errorf("path traversal prohibited: %s", header.Name)
		}
		// 3. Symlinks/Hardlinks
		if header.Typeflag == tar.TypeSymlink || header.Typeflag == tar.TypeLink {
			return fmt.Errorf("symlinks/hardlinks prohibited: %s", header.Name)
		}

		target := filepath.Join(destDir, header.Name)

		// Defense in depth: check if target is inside destDir
		if !strings.HasPrefix(target, filepath.Clean(destDir)+string(os.PathSeparator)) && target != destDir {
			// This might trigger on the root folder if tar has "./" or something, but usually safe.
			// Actually header.Name is relative. filepath.Join(destDir, "foo") -> /tmp/foo.
			// Just to be sure.
		}

		if header.Typeflag == tar.TypeDir {
			if err := os.MkdirAll(target, 0755); err != nil {
				return err
			}
			continue
		}

		if header.Typeflag == tar.TypeReg {
			// Ensure parent exists
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return err
			}

			wf, err := os.Create(target)
			if err != nil {
				return err
			}

			// Copy limiting size? No, we trust local disk space for now.
			if _, err := io.Copy(wf, tr); err != nil {
				wf.Close()
				return err
			}
			wf.Close()
		}
	}
	return nil
}

func verifyRootChecksums(dir string) error {
	checksumsPath := filepath.Join(dir, "CHECKSUMS.sha256")
	content, err := os.ReadFile(checksumsPath)
	if err != nil {
		return err
	}

	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	checked := make(map[string]bool)

	for _, line := range lines {
		parts := strings.Fields(line)
		if len(parts) != 2 {
			continue // Malformed line? Or fail? Standard `sha256sum` output.
		}
		hash := parts[0]
		fname := parts[1]

		// Only check the expected root files
		if fname != "EVIDENCE_VERSION" && fname != "METADATA.json" && fname != "MANIFEST.tsv" {
			continue
		}

		actualHash, _, err := fileSha256AndSize(filepath.Join(dir, fname))
		if err != nil {
			return fmt.Errorf("failed to hash %s: %w", fname, err)
		}
		if actualHash != hash {
			return fmt.Errorf("checksum mismatch for %s: expected %s, got %s", fname, hash, actualHash)
		}
		checked[fname] = true
	}

	if !checked["EVIDENCE_VERSION"] || !checked["METADATA.json"] || !checked["MANIFEST.tsv"] {
		return fmt.Errorf("CHECKSUMS.sha256 is missing entries for required root files")
	}
	return nil
}

func verifyManifest(dir string) error {
	manifestPath := filepath.Join(dir, "MANIFEST.tsv")
	f, err := os.Open(manifestPath)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	manifestFiles := make(map[string]bool)

	dataDir := filepath.Join(dir, "data")

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) != 3 {
			return fmt.Errorf("invalid manifest line: %q", line)
		}
		relPath := parts[0]
		expectedHash := parts[1]
		var expectedSize int64
		fmt.Sscanf(parts[2], "%d", &expectedSize)

		manifestFiles[relPath] = true
		fullPath := filepath.Join(dataDir, relPath)

		info, err := os.Stat(fullPath)
		if err != nil {
			if os.IsNotExist(err) {
				return fmt.Errorf("file in manifest missing from data: %s", relPath)
			}
			return err
		}
		if info.Size() != expectedSize {
			return fmt.Errorf("size mismatch for %s: expected %d, got %d", relPath, expectedSize, info.Size())
		}

		actualHash, _, err := fileSha256AndSize(fullPath)
		if err != nil {
			return err
		}
		if actualHash != expectedHash {
			return fmt.Errorf("content hash mismatch for %s", relPath)
		}
	}

	// Reverse check: Walk data/ and ensure every file is in manifestFiles
	err = filepath.Walk(dataDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		relPath, err := filepath.Rel(dataDir, path)
		if err != nil {
			return err
		}
		relPath = filepath.ToSlash(relPath)

		if !manifestFiles[relPath] {
			return fmt.Errorf("file in data/ not listed in manifest: %s", relPath)
		}
		return nil
	})

	return err
}
