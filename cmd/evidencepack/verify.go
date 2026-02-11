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

const (
	policyFile          = "reviewpack_policy.toml"
	keysDirName         = "ops/keys/reviewpack"
	fileEvidenceVersion = "EVIDENCE_VERSION"
	fileMetadata        = "METADATA.json"
	fileManifest        = "MANIFEST.tsv"
	fileChecksums       = "CHECKSUMS.sha256"
	dirData             = "data"
)

func runVerify(args []string) error {
	fs := flag.NewFlagSet("verify", flag.ExitOnError)
	packPath := fs.String("pack", "", "Path to evidence pack file")
	policyMode := fs.String("policy-mode", "", "Policy mode (auto, local, ci)")
	policyPath := fs.String("policy", "", "Path to policy file (overrides default/bundled)")
	keysDir := fs.String("keys-dir", "", "Path to keys directory (overrides default/bundled)")

	if err := fs.Parse(args); err != nil {
		return err
	}

	if *packPath == "" {
		if fs.NArg() > 0 {
			*packPath = fs.Arg(0)
		} else {
			return fmt.Errorf("--pack or positional argument is required")
		}
	}

	repoRoot := "."
	logger, err := NewAuditLogger(repoRoot)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Warning: Audit logger init failed: %v\n", err)
	}

	cfg := VerifyConfig{
		Path:       *packPath,
		RepoRoot:   repoRoot,
		Logger:     logger,
		PolicyMode: *policyMode,
		PolicyPath: *policyPath,
		KeysDir:    *keysDir,
	}

	return verifyPack(cfg)
}

type VerifyConfig struct {
	Path       string
	RepoRoot   string
	Logger     *AuditLogger
	PolicyMode string
	PolicyPath string
	KeysDir    string
}

func verifyPack(cfg VerifyConfig) error {
	ctx, err := prepareVerificationContext(cfg)
	if err != nil {
		return err
	}
	defer ctx.Cleanup()

	// 1. Structural Verify (v1)
	if err := verifyStructure(ctx.TargetArtifact); err != nil {
		return err
	}

	// 2. Policy Setup
	env := DeterminePolicyEnv(cfg.PolicyMode)
	policy, err := loadPolicySafe(ctx.PolicyPath, env)
	if err != nil {
		return err
	}

	// 3. Signature Check (S7)
	hasSignature, keyID, err := verifySignatureWithAudit(ctx.TargetArtifact, ctx.KeysDir, cfg.Logger)
	if err != nil {
		return err
	}

	// 4. Policy Evaluation (S8)
	if err := EvaluatePolicy(policy, env, hasSignature, keyID); err != nil {
		return formatPolicyError(err, policy, env, keyID, ctx.PolicyPath)
	}

	return nil
}

type verContext struct {
	TargetArtifact string
	PolicyPath     string
	KeysDir        string
	Cleanup        func()
}

func prepareVerificationContext(cfg VerifyConfig) (*verContext, error) {
	ctx := &verContext{
		TargetArtifact: cfg.Path,
		PolicyPath:     filepath.Join(cfg.RepoRoot, "ops", policyFile),
		KeysDir:        filepath.Join(cfg.RepoRoot, keysDirName),
		Cleanup:        func() {}, // Empty cleanup by default
	}

	// Override defaults with user flags if provided
	if cfg.PolicyPath != "" {
		ctx.PolicyPath = cfg.PolicyPath
	}
	if cfg.KeysDir != "" {
		ctx.KeysDir = cfg.KeysDir
	}

	isB, err := isBundle(cfg.Path)
	if err != nil {
		return nil, fmt.Errorf("failed to check bundle status: %w", err)
	}

	if isB {
		return prepareBundleContext(ctx, cfg)
	}
	return ctx, nil
}

func prepareBundleContext(ctx *verContext, cfg VerifyConfig) (*verContext, error) {
	fmt.Println("Input is a PROVENANCE BUNDLE. Unpacking...")
	tmpDir, cleanup, err := unpackBundle(cfg.Path)
	if err != nil {
		return nil, fmt.Errorf("failed to unpack bundle: %w", err)
	}
	ctx.Cleanup = cleanup

	// Redirect to bundle contents
	artDir := filepath.Join(tmpDir, "artifact")
	entries, err := os.ReadDir(artDir)
	if err != nil {
		cleanup()
		return nil, fmt.Errorf("failed to read artifact dir: %w", err)
	}

	var artifacts []string
	for _, e := range entries {
		if e.Type().IsRegular() {
			artifacts = append(artifacts, e.Name())
		}
	}

	if len(artifacts) != 1 {
		cleanup()
		return nil, fmt.Errorf("bundle must contain exactly one artifact file, found %d", len(artifacts))
	}
	ctx.TargetArtifact = filepath.Join(artDir, artifacts[0])

	// Only override if NOT set by user flags
	if cfg.KeysDir == "" {
		ctx.KeysDir = filepath.Join(tmpDir, "keys")
	}
	if cfg.PolicyPath == "" {
		ctx.PolicyPath = filepath.Join(tmpDir, "policy", policyFile)
	}
	return ctx, nil
}

func loadPolicySafe(path, env string) (*ReviewPackPolicy, error) {
	policy, err := LoadPolicy(path)
	if err != nil {
		if env == EnvCI {
			return nil, fmt.Errorf("FATAL: Failed to load policy in CI environment (%s): %w\nSee docs/evidence/RUNBOOK.md for policy recovery.", path, err)
		}
		fmt.Fprintf(os.Stderr, "Warning: Failed to load policy from %s (%v). Proceeding with permissive default.\n", path, err)
		return &ReviewPackPolicy{
			Version:     1,
			Enforcement: EnforcementConfig{ModeLocal: ModePermissive, ModeCI: ModeStrict},
		}, nil
	}
	return policy, nil
}

func verifySignatureWithAudit(path, keysDir string, logger *AuditLogger) (bool, string, error) {
	sigPath, err := locateSignature(path)
	if err != nil {
		// Not found or error
		if os.IsNotExist(err) {
			fmt.Println("No signature found (skipped).")
			return false, "", nil
		}
		return false, "", err
	}

	fmt.Printf("Signature found: %s. Verifying...\n", sigPath)
	verifyErr := verifySignature(path, sigPath, keysDir)
	res := "ok"
	if verifyErr != nil {
		res = "fail"
	}

	var keyID string
	if data, err := os.ReadFile(sigPath); err == nil {
		var sc SignatureSidecar
		if json.Unmarshal(data, &sc) == nil {
			keyID = sc.KeyID
		}
	}

	if logger != nil {
		artSHA, _ := CalculateSHA256(path)
		logger.LogEvent(&AuditEntry{
			EventType:      "verify",
			Result:         res,
			ArtifactPath:   path,
			ArtifactSHA256: artSHA,
			SigPath:        sigPath,
			KeyID:          keyID,
			UTCTimestamp:   time.Now().UTC().Format(time.RFC3339),
		})
	}

	if verifyErr != nil {
		return true, keyID, fmt.Errorf("cryptographic verification failed: %w", verifyErr)
	}

	fmt.Println("Signature VERIFIED.")
	return true, keyID, nil
}

func locateSignature(path string) (string, error) {
	sigPath := path + ".sig.json"
	if _, err := os.Stat(sigPath); err == nil {
		return sigPath, nil
	}

	// Check bundle sibling structure
	dir := filepath.Dir(path)   // tmp/artifact
	parent := filepath.Dir(dir) // tmp
	if filepath.Base(dir) == "artifact" {
		sigName := filepath.Base(path) + ".sig.json"
		altSigPath := filepath.Join(parent, "signature", sigName)
		if _, err := os.Stat(altSigPath); err == nil {
			return altSigPath, nil
		}
	}
	return "", os.ErrNotExist
}

func formatPolicyError(err error, policy *ReviewPackPolicy, env, keyID, policyPath string) error {
	return fmt.Errorf(`
================================================================================
POLICY VIOLATION (%s defined in %s)
Mode: %s (Environment: %s)

Error: %v

ACTION REQUIRED:
1. Check ops/reviewpack_policy.toml
2. If signature required: Sign the artifact (see ops/keys/reviewpack/README.md)
3. If key rejected: Add KeyID %s to 'allowed_key_ids' in policy
================================================================================
`, "v1", policyPath, policy.Enforcement.ModeCI, env, err, keyID)
}

func isBundle(path string) (bool, error) {
	f, err := os.Open(path)
	if err != nil {
		return false, err
	}
	defer f.Close()

	gzr, err := gzip.NewReader(f)
	if err != nil {
		return false, err // Not a gzip -> Not a bundle
	}
	defer gzr.Close()

	tr := tar.NewReader(gzr)
	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return false, err
		}
		if header.Name == "BUNDLE_VERSION" {
			return true, nil
		}
	}
	return false, nil
}

func unpackBundle(path string) (string, func(), error) {
	tmpDir, err := os.MkdirTemp("", "bundle_unpack_*")
	if err != nil {
		return "", nil, err
	}
	cleanup := func() { os.RemoveAll(tmpDir) }

	// Re-open/read to extract
	if err := extractAndVerifySafety(path, tmpDir); err != nil {
		cleanup()
		return "", nil, err
	}

	// Verify BUNDLE_VERSION
	vBytes, err := os.ReadFile(filepath.Join(tmpDir, "BUNDLE_VERSION"))
	if err != nil {
		cleanup()
		return "", nil, fmt.Errorf("failed to read BUNDLE_VERSION: %w", err)
	}
	if string(vBytes) != "1\n" {
		cleanup()
		return "", nil, fmt.Errorf("unknown BUNDLE_VERSION: %q", string(vBytes))
	}

	// Verify Manifest
	manPath := filepath.Join(tmpDir, "manifest", "BUNDLE_MANIFEST.tsv")
	if _, err := os.Stat(manPath); err != nil {
		cleanup()
		return "", nil, fmt.Errorf("mandatory bundle manifest missing: %w", err)
	}
	if err := verifyBundleManifest(tmpDir, manPath); err != nil {
		cleanup()
		return "", nil, fmt.Errorf("bundle manifest verification failed: %w", err)
	}
	return tmpDir, cleanup, nil
}

func verifyBundleManifest(rootDir, manifestPath string) error {
	f, err := os.Open(manifestPath)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "\t", 2)
		if len(parts) != 2 {
			return fmt.Errorf("invalid manifest line: %s", line)
		}
		sha := parts[0]
		relPath := parts[1]

		fullPath := filepath.Join(rootDir, relPath)
		actualSha, _, err := fileSha256AndSize(fullPath)
		if err != nil {
			return fmt.Errorf("failed to check file %s: %w", relPath, err)
		}
		if actualSha != sha {
			return fmt.Errorf("checksum mismatch for %s", relPath)
		}
	}
	return nil
}

// verifyStructure checks the inner contents of the pack
func verifyStructure(path string) error {
	tempDir, err := os.MkdirTemp("", "evidence_verify_")
	if err != nil {
		return fmt.Errorf("failed to create temp dir: %w", err)
	}
	defer os.RemoveAll(tempDir)

	if err := extractAndVerifySafety(path, tempDir); err != nil {
		return fmt.Errorf("safety check failed: %w", err)
	}

	if err := checkRootEntries(tempDir); err != nil {
		return err
	}
	if err := checkEvidenceVersion(tempDir); err != nil {
		return err
	}
	if err := verifyRootChecksums(tempDir); err != nil {
		return fmt.Errorf("checksum verification failed: %w", err)
	}
	if err := verifyManifest(tempDir); err != nil {
		return fmt.Errorf("manifest verification failed: %w", err)
	}

	fmt.Printf("VERIFIED: %s\n", path)
	return nil
}

func checkRootEntries(dir string) error {
	allowed := map[string]bool{
		fileEvidenceVersion: true,
		fileMetadata:        true,
		fileManifest:        true,
		fileChecksums:       true,
		dirData:             true,
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return fmt.Errorf("failed to read extracted root: %w", err)
	}

	for _, entry := range entries {
		name := entry.Name()
		if !allowed[name] {
			return fmt.Errorf("forbidden root entry: %s", name)
		}
	}

	required := []string{fileEvidenceVersion, fileMetadata, fileManifest, fileChecksums, dirData}
	for _, req := range required {
		info, err := os.Stat(filepath.Join(dir, req))
		if err != nil {
			if os.IsNotExist(err) {
				return fmt.Errorf("missing required item: %s", req)
			}
			return err
		}
		if req == dirData && !info.IsDir() {
			return fmt.Errorf("data must be a directory")
		}
		if req != dirData && info.IsDir() {
			return fmt.Errorf("%s must be a file", req)
		}
	}
	return nil
}

func checkEvidenceVersion(dir string) error {
	verBytes, err := os.ReadFile(filepath.Join(dir, fileEvidenceVersion))
	if err != nil {
		return fmt.Errorf("failed to read EVIDENCE_VERSION: %w", err)
	}
	if string(verBytes) != "v1\n" {
		return fmt.Errorf("invalid EVIDENCE_VERSION: %q (expected 'v1\\n')", string(verBytes))
	}
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
		if err := safeExtractHeader(tr, header, destDir); err != nil {
			return err
		}
	}
	return nil
}

func safeExtractHeader(tr *tar.Reader, header *tar.Header, destDir string) error {
	// Safety Checks
	if filepath.IsAbs(header.Name) || strings.HasPrefix(header.Name, "/") {
		return fmt.Errorf("absolute path prohibited: %s", header.Name)
	}
	clean := filepath.Clean(header.Name)
	if strings.HasPrefix(clean, "..") || strings.Contains(clean, "/../") || strings.HasSuffix(clean, "/..") {
		return fmt.Errorf("path traversal prohibited: %s", header.Name)
	}
	if header.Typeflag == tar.TypeSymlink || header.Typeflag == tar.TypeLink {
		return fmt.Errorf("symlinks/hardlinks prohibited: %s", header.Name)
	}

	target := filepath.Join(destDir, header.Name)
	// Defense in depth
	if !strings.HasPrefix(target, filepath.Clean(destDir)+string(os.PathSeparator)) && target != destDir {
		// potential escape
	}

	if header.Typeflag == tar.TypeDir {
		return os.MkdirAll(target, 0755)
	}

	if header.Typeflag == tar.TypeReg {
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		wf, err := os.Create(target)
		if err != nil {
			return err
		}
		defer wf.Close()
		if _, err := io.Copy(wf, tr); err != nil {
			return err
		}
	}
	return nil
}

func verifyRootChecksums(dir string) error {
	checksumsPath := filepath.Join(dir, fileChecksums)
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
		if fname != fileEvidenceVersion && fname != fileMetadata && fname != fileManifest {
			continue
		}

		actualHash, _, err := fileSha256AndSize(filepath.Join(dir, fname))
		if err != nil {
			return fmt.Errorf("failed to hash %s: %w", fname, err)
		}
		if actualHash != hash {
			return fmt.Errorf("checksum mismatch for %s", fname)
		}
		checked[fname] = true
	}

	if !checked[fileEvidenceVersion] || !checked[fileMetadata] || !checked[fileManifest] {
		return fmt.Errorf("%s is missing entries for required root files", fileChecksums)
	}
	return nil
}

func verifyManifest(dir string) error {
	manifestPath := filepath.Join(dir, fileManifest)
	f, err := os.Open(manifestPath)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	manifestFiles := make(map[string]bool)

	dataDir := filepath.Join(dir, dirData)

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
