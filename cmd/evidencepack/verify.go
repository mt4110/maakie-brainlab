package main

import (
	"archive/tar"
	"bufio"
	"compress/gzip"
	"crypto/ed25519"
	"encoding/base64"
	"encoding/hex"
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
	dirSignatures       = "SIGNATURES"
)

func runVerify(args []string) error {
	fs := flag.NewFlagSet("verify", flag.ExitOnError)
	packPath := fs.String("pack", "", "Path to evidence pack file")
	policyMode := fs.String("policy-mode", "", "Policy mode (auto, local, ci)")
	policyPath := fs.String("policy", "", "Path to policy file (overrides default/bundled)")
	keysDir := fs.String("keys-dir", "", "Path to keys directory (overrides default/bundled)")

	repo := fs.String("repo", ".", "Repository root directory (for audit chain)")
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

	repoRoot := *repo
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

	// 3. Signature Check — try embedded first, then sidecar
	hasSignature := false
	var keyID string
	var pubKeySHA256 string
	var pubKeySource string

	// 3a. Embedded signatures (SIGNATURES/ inside tar)
	embedded, embedKeyID, embedFP, embedErr := verifyEmbeddedSignature(ctx.TargetArtifact)
	if embedErr != nil {
		return embedErr
	}
	if embedded {
		hasSignature = true
		keyID = embedKeyID
		pubKeySHA256 = embedFP
		pubKeySource = "embedded"
	} else {
		// 3b. Legacy sidecar signatures
		hasSignature, keyID, err = verifySignatureWithAudit(ctx.TargetArtifact, ctx.KeysDir, cfg.Logger)
		if err != nil {
			return err
		}
		if hasSignature {
			pubKeySource = "file:" + ctx.KeysDir
			pubKeySHA256 = computeSidecarFingerprint(ctx.TargetArtifact, ctx.KeysDir, keyID)
		}
	}

	// Always log signer identity
	if hasSignature {
		fmt.Printf("  KeyID:        %s\n", keyID)
		fmt.Printf("  PubKeySHA256: %s\n", pubKeySHA256)
		fmt.Printf("  PubKeySource: %s\n", pubKeySource)

		if policy.Keys.PrimaryPubkeySHA256 != "" {
			isPrimary := strings.EqualFold(pubKeySHA256, policy.Keys.PrimaryPubkeySHA256)
			fmt.Printf("  PrimaryPubKeySHA256: %s\n", policy.Keys.PrimaryPubkeySHA256)
			fmt.Printf("  SignerIsPrimary:     %v\n", isPrimary)
			if !isPrimary {
				fmt.Printf("  [WARN] signer is not primary (rotation state)\n")
			}
		}
	}

	// 4. Policy Evaluation (S8 + Trust Anchor v1)
	if err := EvaluatePolicy(policy, env, hasSignature, keyID, pubKeySHA256); err != nil {
		return formatPolicyError(err, policy, env, keyID, pubKeySHA256, ctx.PolicyPath)
	}

	// 5. Audit Chain Verification (S10) — if present in bundle
	if err := verifyBundleAudit(ctx); err != nil {
		return err
	}

	return nil
}

type verContext struct {
	TargetArtifact string
	PolicyPath     string
	KeysDir        string
	BundleDir      string // root of unpacked bundle (empty if not a bundle)
	Cleanup        func()
}

func prepareVerificationContext(cfg VerifyConfig) (*verContext, error) {
	ctx := &verContext{
		TargetArtifact: cfg.Path,
		PolicyPath:     filepath.Join(cfg.RepoRoot, "ops", policyFile),
		KeysDir:        filepath.Join(cfg.RepoRoot, keysDirName),
		Cleanup:        func() { /* no-op: overridden by prepareBundleContext when needed */ },
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
	ctx.BundleDir = tmpDir

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

// VerifyError wraps an error with a specific exit code.
type VerifyError struct {
	Code    int
	Message string
}

func (e *VerifyError) Error() string { return e.Message }

// verifyBundleAudit checks for an embedded audit log in the bundle and verifies it.
// If no audit log exists, it returns nil (pass).
// Uses the new TSV-based ValidateChain.
func verifyBundleAudit(ctx *verContext) error {
	if ctx.BundleDir == "" {
		// Not a bundle — skip
		return nil
	}

	// S10-00: Check for TSV chain first (v1 spec)
	chainPath := filepath.Join(ctx.BundleDir, "audit", ChainFile)
	if _, err := os.Stat(chainPath); err != nil {
		if os.IsNotExist(err) {
			// Optional: Fallback to checking legacy jsonl if we wanted backward compat,
			// but for v1 strictness we just say "no chain found" and pass.
			fmt.Println("No audit chain in bundle (skipped).")
			return nil
		}
		return &VerifyError{Code: ExitIOError, Message: fmt.Sprintf("failed to check audit chain in bundle: %v", err)}
	}

	fmt.Println("Audit chain found in bundle. Verifying...")
	diags, err := ValidateChain(chainPath)
	if err != nil {
		return &VerifyError{Code: ExitIOError, Message: fmt.Sprintf("chain read error: %v", err)}
	}

	if len(diags) > 0 {
		fails := 0
		for _, d := range diags {
			if d.Severity == "FAIL" {
				fails++
				fmt.Printf("[FAIL] Line %d: %s\n", d.Line, d.Message)
			} else {
				fmt.Printf("[WARN] Line %d: %s\n", d.Line, d.Message)
			}
		}
		if fails > 0 {
			return &VerifyError{Code: ExitTamper, Message: fmt.Sprintf("bundle audit chain verification failed (%d errors)", fails)}
		}
	}

	fmt.Println("Audit chain VERIFIED.")
	return nil
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

// computeSidecarFingerprint loads the public key for a sidecar-signed pack and returns its fingerprint.
// Returns empty string on any error (best-effort for legacy path).
func computeSidecarFingerprint(tarPath, keysDir, keyID string) string {
	if keysDir == "" || keyID == "" {
		return ""
	}
	pubPath := filepath.Join(keysDir, keyID+".pub")
	data, err := os.ReadFile(pubPath)
	if err != nil {
		return ""
	}
	var ck CryptoKey
	if err := json.Unmarshal(data, &ck); err != nil {
		return ""
	}
	pub, err := decodePublicKey(ck.PubB64)
	if err != nil {
		return ""
	}
	return PubKeyFingerprint(pub)
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

func formatPolicyError(err error, policy *ReviewPackPolicy, env, keyID, pubKeySHA256, policyPath string) error {
	errMsg := err.Error()
	howToFix := "See docs/evidence/SIGNING_CONTRACT_v1.md for policy recovery."

	if strings.Contains(errMsg, "is revoked") {
		howToFix = "remove key from signer / rotate key, update policy revoked/allowed"
	} else if strings.Contains(errMsg, "not in allowlist") {
		howToFix = "add fingerprint to allowed_pubkey_sha256 (and optionally set primary)"
	}

	return fmt.Errorf(`
================================================================================
POLICY VIOLATION (Trust Anchor v1)
Policy Path: %s
Mode:        %s (Environment: %s)

Error: %v

KeyID:        %s
PubKeySHA256: %s

HOW-TO-FIX:
%s

Note: KeyID is a label; allowlist is enforced by PubKeySHA256
================================================================================
`, policyPath, policy.Enforcement.ModeCI, env, err, keyID, pubKeySHA256, howToFix)
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
		dirSignatures:       true,
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return fmt.Errorf("failed to read extracted root: %w", err)
	}

	for _, entry := range entries {
		if !allowed[entry.Name()] {
			return fmt.Errorf("forbidden root entry: %s", entry.Name())
		}
	}

	return verifyRequiredEntries(dir)
}

// verifyEmbeddedSignature checks for SIGNATURES/ inside the tar and verifies.
// Returns (found, keyID, pubKeySHA256, error).
func verifyEmbeddedSignature(tarPath string) (bool, string, string, error) {
	// Extract SIGNATURES/ files from tar
	sigFiles, err := extractSignatureFiles(tarPath)
	if err != nil {
		return false, "", "", err
	}

	// Check if SIGNATURES/ exists
	sha256Content, hasSHA := sigFiles["SIGNATURES/pack.sha256"]
	sigBytes, hasSig := sigFiles["SIGNATURES/pack.sha256.sig"]
	pubJSON, hasPub := sigFiles["SIGNATURES/pack.pub"]

	if !hasSHA && !hasSig && !hasPub {
		return false, "", "", nil
	}
	if !hasSHA || !hasSig || !hasPub {
		return false, "", "", fmt.Errorf("incomplete SIGNATURES/: need pack.sha256, pack.sha256.sig, pack.pub")
	}

	// Parse claimed digest from pack.sha256
	claimedDigest, err := parsePackSHA256(sha256Content)
	if err != nil {
		return false, "", "", fmt.Errorf("invalid SIGNATURES/pack.sha256: %w", err)
	}

	// Parse public key
	var pubKey CryptoKey
	if err := json.Unmarshal(pubJSON, &pubKey); err != nil {
		return false, "", "", fmt.Errorf("invalid SIGNATURES/pack.pub: %w", err)
	}
	if pubKey.Alg != AlgEd25519 {
		return false, "", "", fmt.Errorf("unsupported alg in pack.pub: %s", pubKey.Alg)
	}
	pub, err := decodePublicKey(pubKey.PubB64)
	if err != nil {
		return false, "", "", err
	}

	// Compute fingerprint (Trust Anchor v1)
	fingerprint := PubKeyFingerprint(pub)

	// Verify signature over digest
	if !VerifyDigest(claimedDigest, sigBytes, pub) {
		return true, pubKey.KeyID, fingerprint, fmt.Errorf("embedded signature verification FAILED")
	}

	// Verify integrity: recompute SHA256 of CHECKSUMS.sha256 from tar
	actualChkDigest, err := extractAndHashChecksums(tarPath)
	if err != nil {
		return true, pubKey.KeyID, fingerprint, fmt.Errorf("failed to verify CHECKSUMS.sha256 integrity: %w", err)
	}
	if actualChkDigest != claimedDigest {
		return true, pubKey.KeyID, fingerprint, fmt.Errorf(
			"CHECKSUMS.sha256 digest mismatch: claimed %s, actual %s", claimedDigest, actualChkDigest)
	}

	fmt.Printf("Embedded signature VERIFIED (KeyID: %s)\n", pubKey.KeyID)
	return true, pubKey.KeyID, fingerprint, nil
}

// extractSignatureFiles reads SIGNATURES/* entries from a tar.gz.
func extractSignatureFiles(tarPath string) (map[string][]byte, error) {
	f, err := os.Open(tarPath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	gzr, err := gzip.NewReader(f)
	if err != nil {
		return nil, err
	}
	defer gzr.Close()

	result := make(map[string][]byte)
	tr := tar.NewReader(gzr)
	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if strings.HasPrefix(header.Name, "SIGNATURES/") && header.Typeflag == tar.TypeReg {
			data, err := io.ReadAll(tr)
			if err != nil {
				return nil, err
			}
			result[header.Name] = data
		}
	}
	return result, nil
}

// parsePackSHA256 extracts the hex digest from "<hex>  CHECKSUMS.sha256\n" format.
func parsePackSHA256(content []byte) (string, error) {
	line := strings.TrimSpace(string(content))
	parts := strings.Fields(line)
	if len(parts) != 2 || parts[1] != "CHECKSUMS.sha256" {
		return "", fmt.Errorf("unexpected format: %q", line)
	}
	// Validate hex
	if len(parts[0]) != 64 {
		return "", fmt.Errorf("invalid SHA256 hex length: %d", len(parts[0]))
	}
	if _, err := hex.DecodeString(parts[0]); err != nil {
		return "", fmt.Errorf("invalid hex: %w", err)
	}
	return parts[0], nil
}

// decodePublicKey decodes a base64-encoded Ed25519 public key.
func decodePublicKey(b64 string) (ed25519.PublicKey, error) {
	pubBytes, err := base64.StdEncoding.DecodeString(b64)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 in public key: %w", err)
	}
	if len(pubBytes) != ed25519.PublicKeySize {
		return nil, fmt.Errorf("invalid Ed25519 public key length: %d", len(pubBytes))
	}
	return ed25519.PublicKey(pubBytes), nil
}

func verifyRequiredEntries(dir string) error {
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
	target, err := validateExtractPath(header, destDir)
	if err != nil {
		return err
	}

	if header.Typeflag == tar.TypeDir {
		return os.MkdirAll(target, 0755)
	}

	if header.Typeflag == tar.TypeReg {
		return extractRegularFile(tr, target)
	}
	return nil
}

func validateExtractPath(header *tar.Header, destDir string) (string, error) {
	// Safety Checks
	if filepath.IsAbs(header.Name) || strings.HasPrefix(header.Name, "/") {
		return "", fmt.Errorf("absolute path prohibited: %s", header.Name)
	}
	clean := filepath.Clean(header.Name)
	if strings.HasPrefix(clean, "..") || strings.Contains(clean, "/../") || strings.HasSuffix(clean, "/..") {
		return "", fmt.Errorf("path traversal prohibited: %s", header.Name)
	}
	if header.Typeflag == tar.TypeSymlink || header.Typeflag == tar.TypeLink {
		return "", fmt.Errorf("symlinks/hardlinks prohibited: %s", header.Name)
	}

	target := filepath.Join(destDir, clean)
	// Defense in depth: ensure target stays within destDir after cleaning
	destClean := filepath.Clean(destDir)
	targetClean := filepath.Clean(target)

	if targetClean != destClean && !strings.HasPrefix(targetClean, destClean+string(os.PathSeparator)) {
		return "", fmt.Errorf("bundle extract escape detected: name=%q target=%q dest=%q", header.Name, targetClean, destClean)
	}
	return target, nil
}

func extractRegularFile(tr *tar.Reader, target string) error {
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
		relPath, err := verifyManifestEntry(line, dataDir)
		if err != nil {
			return err
		}
		manifestFiles[relPath] = true
	}

	return checkDataFilesInManifest(dataDir, manifestFiles)
}

func verifyManifestEntry(line, dataDir string) (string, error) {
	parts := strings.Split(line, "\t")
	if len(parts) != 3 {
		return "", fmt.Errorf("invalid manifest line: %q", line)
	}
	relPath := parts[0]
	expectedHash := parts[1]
	var expectedSize int64
	fmt.Sscanf(parts[2], "%d", &expectedSize)

	fullPath := filepath.Join(dataDir, relPath)

	info, err := os.Stat(fullPath)
	if err != nil {
		if os.IsNotExist(err) {
			return "", fmt.Errorf("file in manifest missing from data: %s", relPath)
		}
		return "", err
	}
	if info.Size() != expectedSize {
		return "", fmt.Errorf("size mismatch for %s: expected %d, got %d", relPath, expectedSize, info.Size())
	}

	actualHash, _, err := fileSha256AndSize(fullPath)
	if err != nil {
		return "", err
	}
	if actualHash != expectedHash {
		return "", fmt.Errorf("content hash mismatch for %s", relPath)
	}
	return relPath, nil
}

func checkDataFilesInManifest(dataDir string, manifestFiles map[string]bool) error {
	return filepath.Walk(dataDir, func(path string, info os.FileInfo, err error) error {
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
}
