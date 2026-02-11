package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

func runBundle(args []string) error {
	fs := flag.NewFlagSet("bundle", flag.ExitOnError)
	artifactPath := fs.String("artifact", "", "Path to the input artifact (tar.gz)")
	policyPath := fs.String("policy", "ops/reviewpack_policy.toml", "Path to policy file")
	keysDir := fs.String("keys-dir", "ops/keys/reviewpack", "Path to keys directory")
	outPath := fs.String("out", "", "Output bundle path (optional, auto-generated if empty)")
	auditDir := fs.String("audit-dir", "", "Path to audit log directory (optional, embeds audit snapshot)")

	if err := fs.Parse(args); err != nil {
		return err
	}
	if *artifactPath == "" {
		return fmt.Errorf("--artifact is required")
	}

	stagingDir, err := prepareStagingDir()
	if err != nil {
		return err
	}
	defer os.RemoveAll(stagingDir)

	if err := copyArtifact(stagingDir, *artifactPath); err != nil {
		return err
	}

	if err := handleSignatureAndKeys(stagingDir, *artifactPath, *keysDir); err != nil {
		return err
	}

	if err := copyPolicy(stagingDir, *policyPath); err != nil {
		return err
	}

	if err := copyAuditIfPresent(stagingDir, *auditDir); err != nil {
		return err
	}

	if err := createReadme(stagingDir); err != nil {
		return err
	}

	if err := createManifest(stagingDir); err != nil {
		return err
	}

	return createBundleTar(stagingDir, *artifactPath, *outPath)
}

func prepareStagingDir() (string, error) {
	stagingDir, err := os.MkdirTemp("", "bundle_staging_*")
	if err != nil {
		return "", fmt.Errorf("failed to create staging dir: %w", err)
	}
	if err := os.WriteFile(filepath.Join(stagingDir, "BUNDLE_VERSION"), []byte("1\n"), 0644); err != nil {
		os.RemoveAll(stagingDir)
		return "", fmt.Errorf("failed to write BUNDLE_VERSION: %w", err)
	}
	return stagingDir, nil
}

func copyArtifact(stagingDir, artifactPath string) error {
	artDst := filepath.Join(stagingDir, "artifact")
	if err := os.MkdirAll(artDst, 0755); err != nil {
		return fmt.Errorf("failed to create artifact dir: %w", err)
	}
	if err := copyFile(artifactPath, filepath.Join(artDst, filepath.Base(artifactPath))); err != nil {
		return fmt.Errorf("failed to copy artifact: %w", err)
	}
	return nil
}

func handleSignatureAndKeys(stagingDir, artifactPath, keysDir string) error {
	sigPath := artifactPath + ".sig.json"
	sigDst := filepath.Join(stagingDir, "signature")
	keysDst := filepath.Join(stagingDir, "keys")

	if err := os.MkdirAll(sigDst, 0755); err != nil {
		return fmt.Errorf("failed to create signature dir: %w", err)
	}
	if err := os.MkdirAll(keysDst, 0755); err != nil {
		return fmt.Errorf("failed to create keys dir: %w", err)
	}

	if _, err := os.Stat(sigPath); err != nil {
		// No signature - warn but proceed
		fmt.Printf("Warning: No signature found at %s. Bundle will verify as unsigned.\n", sigPath)
		return nil
	}

	// Copy Signature
	if err := copyFile(sigPath, filepath.Join(sigDst, filepath.Base(sigPath))); err != nil {
		return fmt.Errorf("failed to copy signature: %w", err)
	}

	// Read sig to get key_id
	sigBytes, err := os.ReadFile(sigPath)
	if err != nil {
		return fmt.Errorf("failed to read signature: %w", err)
	}
	var sc SignatureSidecar
	if err := json.Unmarshal(sigBytes, &sc); err != nil {
		return fmt.Errorf("failed to parse signature: %w", err)
	}

	// Find and copy key
	keyPath := filepath.Join(keysDir, sc.KeyID+".pub")
	if _, err := os.Stat(keyPath); err != nil {
		return fmt.Errorf("public key for %s not found in %s: %w", sc.KeyID, keysDir, err)
	}
	if err := copyFile(keyPath, filepath.Join(keysDst, sc.KeyID+".pub")); err != nil {
		return fmt.Errorf("failed to copy public key: %w", err)
	}
	return nil
}

func copyPolicy(stagingDir, policyPath string) error {
	policyDst := filepath.Join(stagingDir, "policy")
	if err := os.MkdirAll(policyDst, 0755); err != nil {
		return fmt.Errorf("failed to create policy dir: %w", err)
	}
	if err := copyFile(policyPath, filepath.Join(policyDst, "reviewpack_policy.toml")); err != nil {
		return fmt.Errorf("failed to copy policy from %s: %w", policyPath, err)
	}
	return nil
}

// copyAuditIfPresent embeds an audit log snapshot into the bundle if auditDir is provided.
func copyAuditIfPresent(stagingDir, auditDir string) error {
	if auditDir == "" {
		return nil
	}

	// S10-00: Copy TSV audit chain
	srcPath := filepath.Join(auditDir, ChainFile)
	if _, err := os.Stat(srcPath); err != nil {
		if os.IsNotExist(err) {
			fmt.Println("No audit chain found; skipping audit embed.")
			return nil
		}
		return fmt.Errorf("failed to check audit chain: %w", err)
	}

	auditDst := filepath.Join(stagingDir, "audit")
	if err := os.MkdirAll(auditDst, 0755); err != nil {
		return fmt.Errorf("failed to create audit dir in bundle: %w", err)
	}
	if err := copyFile(srcPath, filepath.Join(auditDst, ChainFile)); err != nil {
		return fmt.Errorf("failed to copy audit chain: %w", err)
	}
	fmt.Println("Embedded audit chain snapshot in bundle.")
	return nil
}

func createReadme(stagingDir string) error {
	readmeContent := `
# Provenance Bundle v1

To verify this bundle:
    evidencepack verify <path_to_bundle>

Contents:
- artifact/: The artifact being protected.
- signature/: Detached signature for the artifact.
- policy/: Snapshot of policy used at bundle time.
- keys/: Public keys needed for verification.
- audit/: (Optional) Audit chain snapshot for provenance verification.

NOTE: The signature protects the *artifact only*.
The policy and keys are provided for self-contained verification, but their
authenticity is not strictly guaranteed by the bundle signature itself in v1.
`
	if err := os.WriteFile(filepath.Join(stagingDir, "README.md"), []byte(strings.TrimSpace(readmeContent)+"\n"), 0644); err != nil {
		return fmt.Errorf("failed to write README.md: %w", err)
	}
	return nil
}

func createManifest(stagingDir string) error {
	manifestDst := filepath.Join(stagingDir, "manifest")
	if err := os.MkdirAll(manifestDst, 0755); err != nil {
		return fmt.Errorf("failed to create manifest dir: %w", err)
	}

	manifestLines, err := generateBundleManifest(stagingDir)
	if err != nil {
		return fmt.Errorf("failed to generate manifest: %w", err)
	}

	manifestPath := filepath.Join(manifestDst, "BUNDLE_MANIFEST.tsv")
	if err := os.WriteFile(manifestPath, []byte(strings.Join(manifestLines, "\n")+"\n"), 0644); err != nil {
		return fmt.Errorf("failed to write bundle manifest: %w", err)
	}
	return nil
}

func generateBundleManifest(baseDir string) ([]string, error) {
	var lines []string
	err := filepath.Walk(baseDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		relPath, err := filepath.Rel(baseDir, path)
		if err != nil {
			return err
		}
		relPath = filepath.ToSlash(relPath)

		hash, _, err := fileSha256AndSize(path)
		if err != nil {
			return err
		}
		lines = append(lines, fmt.Sprintf("%s\t%s", hash, relPath))
		return nil
	})
	sort.Strings(lines)
	return lines, err
}

func createBundleTar(stagingDir, artifactPath, outPath string) error {
	artName := filepath.Base(artifactPath)
	parts := strings.Split(artName, "_")
	kind := "unknown"
	artSha := "nosha"

	if len(parts) >= 4 && parts[0] == "evidence" {
		kind = parts[1]
		last := parts[len(parts)-1]
		artSha = strings.TrimSuffix(strings.TrimSuffix(last, ".gz"), ".tar")
	} else {
		s, err := CalculateSHA256(artifactPath)
		if err == nil && len(s) > 7 {
			artSha = s[:7]
		}
	}

	tsStr := time.Now().UTC().Format("20060102T150405Z")
	bundleName := fmt.Sprintf("provenance_bundle_%s_%s_%s.tar.gz", kind, tsStr, artSha)

	finalOut := outPath
	if finalOut == "" {
		finalOut = bundleName
	}

	if err := createDeterministicTar(stagingDir, finalOut); err != nil {
		return fmt.Errorf("failed to create bundle tar: %w", err)
	}

	fmt.Printf("Created bundle: %s\n", finalOut)
	return nil
}
