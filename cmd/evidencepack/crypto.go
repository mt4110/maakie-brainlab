package main

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Contract Constants
const (
	SigContractV1 = "reviewpack.sig.v1"
	AlgEd25519    = "ed25519"
)

// CryptoKey represents a public key for verification
type CryptoKey struct {
	KeyID        string `json:"key_id"`
	Alg          string `json:"alg"`
	PubB64       string `json:"pub_b64"`
	CreatedAtUTC string `json:"created_at_utc"`
}

// SignatureSidecar represents the .sig.json file structure
type SignatureSidecar struct {
	Contract        string `json:"contract"`
	Alg             string `json:"alg"`
	KeyID           string `json:"key_id"`
	ArtifactSHA256  string `json:"artifact_sha256"`
	ChecksumsSHA256 string `json:"checksums_sha256"`
	SignatureB64    string `json:"signature_b64"`
}

// CanonicalMessage constructs the strict signing target
func CanonicalMessage(artifactSHA, checksumsSHA string) []byte {
	// Strictly fixed format:
	// reviewpack.sig.v1\n
	// artifact_sha256=<hex>\n
	// checksums_sha256=<hex>\n
	return []byte(fmt.Sprintf("%s\nartifact_sha256=%s\nchecksums_sha256=%s\n",
		SigContractV1, artifactSHA, checksumsSHA))
}

// CalculateSHA256 returns hex digest of file
func CalculateSHA256(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

// Key Management

// LoadPrivateKey loads Ed25519 private key from file or env
// Returns key, keyID (if available/derived), error
func LoadPrivateKey(file string) (ed25519.PrivateKey, error) {
	var keyBytes []byte
	var err error

	// 1. Try file
	if file != "" {
		content, err := os.ReadFile(file)
		if err != nil {
			return nil, fmt.Errorf("failed to read key file: %w", err)
		}
		trimmed := strings.TrimSpace(string(content))
		// Try raw bytes or base64
		keyBytes, err = base64.StdEncoding.DecodeString(trimmed)
		if err != nil {
			// If not base64, assume raw bytes? No, contract says base64 or raw.
			// Actually file input can be raw 32/64 bytes or base64.
			// Let's try to interpret `content` as raw if base64 fails?
			// But `trimmed` might corrupt raw bytes if they happen to end in newline.
			// Re-read strictly.
			if len(content) == 32 || len(content) == 64 {
				keyBytes = content
			} else {
				// Retry base64 on trimmed string
				return nil, fmt.Errorf("invalid key file format (not base64 or raw 32/64 bytes)")
			}
		}
	} else {
		// 2. Try Env
		envVal := os.Getenv("REVIEWPACK_PRIVATE_KEY_B64")
		if envVal == "" {
			return nil, nil // No key supplied
		}
		keyBytes, err = base64.StdEncoding.DecodeString(strings.TrimSpace(envVal))
		if err != nil {
			return nil, fmt.Errorf("invalid REVIEWPACK_PRIVATE_KEY_B64: %w", err)
		}
	}

	if len(keyBytes) == 32 {
		return ed25519.NewKeyFromSeed(keyBytes), nil
	}
	if len(keyBytes) == 64 {
		return ed25519.PrivateKey(keyBytes), nil
	}
	return nil, fmt.Errorf("invalid key length: %d (want 32 seed or 64 private)", len(keyBytes))
}

// LoadPublicKey loads a specific public key from ops/keys/reviewpack
func LoadPublicKey(repoRoot, keyID string) (ed25519.PublicKey, error) {
	path := filepath.Join(repoRoot, "ops", "keys", "reviewpack", keyID+".pub")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("public key not found for %s: %w", keyID, err)
	}

	var pubKeyMeta CryptoKey
	// Try parsing as JSON first (as per contract choice)
	if err := json.Unmarshal(data, &pubKeyMeta); err != nil {
		// Fallback or just error. Contract says "JSON or TOML". Let's stick to JSON for now as implementation choice.
		return nil, fmt.Errorf("failed to parse public key %s: %w", path, err)
	}

	if pubKeyMeta.Alg != AlgEd25519 {
		return nil, fmt.Errorf("unsupported alg %s in key %s", pubKeyMeta.Alg, keyID)
	}

	pubBytes, err := base64.StdEncoding.DecodeString(pubKeyMeta.PubB64)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 in public key %s: %w", keyID, err)
	}
	if len(pubBytes) != 32 {
		return nil, fmt.Errorf("invalid Ed25519 public key length %d", len(pubBytes))
	}

	return ed25519.PublicKey(pubBytes), nil
}

// findKeyID scans ops/keys/reviewpack/*.pub to find the KeyID for a given public key
func findKeyID(pub ed25519.PublicKey, repoRoot string) (string, error) {
	pattern := filepath.Join(repoRoot, "ops", "keys", "reviewpack", "*.pub")
	matches, err := filepath.Glob(pattern)
	if err != nil {
		return "", fmt.Errorf("glob failed: %w", err)
	}

	targetB64 := base64.StdEncoding.EncodeToString(pub)

	for _, m := range matches {
		data, err := os.ReadFile(m)
		if err != nil {
			continue
		}
		var k CryptoKey
		if json.Unmarshal(data, &k) == nil {
			if k.PubB64 == targetB64 {
				return k.KeyID, nil
			}
		}
	}
	return "", fmt.Errorf("no matching public key found in %s", pattern)
}

// Verification Logic

// verifySignature checks the sidecar against the pack
func verifySignature(packPath, sigPath string) error {
	// 1. Read Sidecar
	data, err := os.ReadFile(sigPath)
	if err != nil {
		return fmt.Errorf("failed to read signature file: %w", err)
	}

	var sc SignatureSidecar
	if err := json.Unmarshal(data, &sc); err != nil {
		return fmt.Errorf("failed to parse signature JSON: %w", err)
	}

	// 2. Check Contract & Alg
	if sc.Contract != SigContractV1 {
		return fmt.Errorf("unsupported contract: %s", sc.Contract)
	}
	if sc.Alg != AlgEd25519 {
		return fmt.Errorf("unsupported alg: %s", sc.Alg)
	}

	// 3. Load Public Key
	// Need repo root. Assuming we run from root or can find it?
	// RunAlways runs from repo root.
	repoRoot := "."
	// If we are in a subdir, this might fail.
	// We can try to find .git or just assume "." for S7 RunAlways context.

	pubKey, err := LoadPublicKey(repoRoot, sc.KeyID)
	if err != nil {
		return fmt.Errorf("failed to load public key %s: %w", sc.KeyID, err)
	}

	// 4. Verify Signature (Unamended)
	// Canonical Input = Claimed SHA + Claimed Checksums SHA
	msg := CanonicalMessage(sc.ArtifactSHA256, sc.ChecksumsSHA256)

	sigBytes, err := base64.StdEncoding.DecodeString(sc.SignatureB64)
	if err != nil {
		return fmt.Errorf("invalid base64 signature: %w", err)
	}

	if !ed25519.Verify(pubKey, msg, sigBytes) {
		return fmt.Errorf("ed25519 signature verification failed")
	}

	// 5. Verify Integrity (Actual vs Claimed)
	actualArtSHA, err := CalculateSHA256(packPath)
	if err != nil {
		return fmt.Errorf("failed to hash artifact: %w", err)
	}
	if actualArtSHA != sc.ArtifactSHA256 {
		return fmt.Errorf("artifact mismatch: claimed %s, actual %s", sc.ArtifactSHA256, actualArtSHA)
	}

	actualChkSHA, err := extractAndHashChecksums(packPath)
	if err != nil {
		return fmt.Errorf("failed to verify checksums.sha256 integrity: %w", err)
	}
	if actualChkSHA != sc.ChecksumsSHA256 {
		return fmt.Errorf("checksums mismatch: claimed %s, actual %s", sc.ChecksumsSHA256, actualChkSHA)
	}

	return nil
}
