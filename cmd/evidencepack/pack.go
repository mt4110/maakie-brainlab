package main

import (
	"archive/tar"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// PackConfig holds configuration for the packing process
type PackConfig struct {
	Kind      string
	StoreDir  string
	Payloads  []string
	Timestamp time.Time
}

// Metadata represents the content of METADATA.json
type Metadata struct {
	Contract        string      `json:"contract"`
	ContractVersion int         `json:"contract_version"`
	CreatedAtUTC    string      `json:"created_at_utc"`
	Kind            string      `json:"kind"`
	Git             GitInfo     `json:"git"`
	PayloadRoot     string      `json:"payload_root"`
	Tool            ToolInfo    `json:"tool"`
	Extensions      interface{} `json:"extensions,omitempty"`
}

type GitInfo struct {
	SHA   string `json:"sha"`
	Dirty bool   `json:"dirty"`
}

type ToolInfo struct {
	Name string `json:"name"`
	Lang string `json:"lang"`
}

func runPack(args []string) error {
	fs := flag.NewFlagSet("pack", flag.ExitOnError)
	kind := fs.String("kind", "", "Kind of evidence")
	store := fs.String("store", ".local/evidence_store", "Store directory")
	sign := fs.Bool("sign", false, "Sign the artifact (requires key)")
	keyFile := fs.String("key-file", "", "Path to private key file")
	if err := fs.Parse(args); err != nil {
		return err
	}

	// Env Override for Sign
	if os.Getenv("REVIEWPACK_SIGN") == "1" {
		*sign = true
	}

	if *kind == "" {
		return fmt.Errorf("--kind is required")
	}
	if err := validateKind(*kind); err != nil {
		return err
	}
	payloads := fs.Args()
	if len(payloads) == 0 {
		return fmt.Errorf("at least one payload path is required")
	}

	config := PackConfig{
		Kind:      *kind,
		StoreDir:  *store,
		Payloads:  payloads,
		Timestamp: time.Now().UTC(),
	}

	packPath, err := executePack(config)
	if err != nil {
		return err
	}

	// Init Audit Logger
	repoRoot := "."
	logger, err := NewAuditLogger(repoRoot)
	if err != nil {
		return fmt.Errorf("audit init failed: %w", err)
	}

	// Sign (Optional)
	if *sign {
		if err := performSigning(packPath, *keyFile, repoRoot, logger); err != nil {
			return fmt.Errorf("signing failed: %w", err)
		}
	}

	// Verify (Mandatory if sig exists)
	if err := verifyPack(packPath, repoRoot, logger); err != nil {
		return fmt.Errorf("post-pack verification failed: %w", err)
	}

	return nil
}

func performSigning(packPath string, keyFile string, repoRoot string, logger *AuditLogger) error {
	privKey, err := LoadPrivateKey(keyFile)
	if err != nil {
		return fmt.Errorf("failed to load private key: %w", err)
	}

	pub := privKey.Public().(ed25519.PublicKey)
	keyID, err := findKeyID(pub, repoRoot)
	if err != nil {
		return fmt.Errorf("key_id lookup failed (ensure public key is in ops/keys/reviewpack): %w", err)
	}

	// Sign
	if err := signArtifact(packPath, privKey, keyID); err != nil {
		logger.LogEvent(&AuditEntry{
			EventType: "sign", Result: "fail", ArtifactPath: packPath, KeyID: keyID, UTCTimestamp: time.Now().UTC().Format(time.RFC3339),
		})
		return err
	}

	artSHA, _ := CalculateSHA256(packPath)
	logger.LogEvent(&AuditEntry{
		EventType: "sign", Result: "ok",
		ArtifactPath: packPath, ArtifactSHA256: artSHA,
		SigPath: packPath + ".sig.json", KeyID: keyID,
		UTCTimestamp: time.Now().UTC().Format(time.RFC3339),
	})

	fmt.Printf("Signed artifact: %s (KeyID: %s)\n", packPath, keyID)
	return nil
}

func signArtifact(packPath string, priv ed25519.PrivateKey, keyID string) error {
	artSHA, err := CalculateSHA256(packPath)
	if err != nil { return err }

	chkSHA, err := extractAndHashChecksums(packPath)
	if err != nil { return err }

	msg := CanonicalMessage(artSHA, chkSHA)
	sig := ed25519.Sign(priv, msg)

	sidecar := SignatureSidecar{
		Contract:        SigContractV1,
		Alg:             AlgEd25519,
		KeyID:           keyID,
		ArtifactSHA256:  artSHA,
		ChecksumsSHA256: chkSHA,
		SignatureB64:    base64.StdEncoding.EncodeToString(sig),
	}

	bytes, _ := json.MarshalIndent(sidecar, "", "  ")
	return os.WriteFile(packPath+".sig.json", bytes, 0644)
}

func extractAndHashChecksums(tarPath string) (string, error) {
	f, err := os.Open(tarPath)
	if err != nil { return "", err }
	defer f.Close()

	gz, err := gzip.NewReader(f)
	if err != nil { return "", err }
	defer gz.Close()

	tr := tar.NewReader(gz)
	for {
		header, err := tr.Next()
		if err == io.EOF { break }
		if err != nil { return "", err }

		if header.Name == "CHECKSUMS.sha256" {
			h := sha256.New()
			if _, err := io.Copy(h, tr); err != nil {
				return "", err
			}
			return hex.EncodeToString(h.Sum(nil)), nil
		}
	}
	return "", fmt.Errorf("CHECKSUMS.sha256 not found in pack")
}

func executePack(cfg PackConfig) (string, error) {
	// 1. Prepare Staging Directory
	stagingDir := filepath.Join(cfg.StoreDir, "tmp", fmt.Sprintf("pack_%d", time.Now().UnixNano()))
	if err := os.MkdirAll(stagingDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create staging dir: %w", err)
	}
	defer os.RemoveAll(stagingDir) // Cleanup on exit

	// 2. Create Directory Structure
	dataDir := filepath.Join(stagingDir, "data")
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create data dir: %w", err)
	}

	// 3. Copy Payloads to data/
	// We flat copy payloads into data/. If collision, we might need a strategy, but for now assume distinct.
	// If payload is a file -> copy to data/basename
	// If payload is a dir -> copy content to data/basename (or recursive)
	for _, p := range cfg.Payloads {
		info, err := os.Stat(p)
		if err != nil {
			return "", fmt.Errorf("failed to stat payload %s: %w", p, err)
		}
		destName := filepath.Base(p)
		destPath := filepath.Join(dataDir, destName)

		if info.IsDir() {
			if err := copyDir(p, destPath); err != nil {
				return "", fmt.Errorf("failed to copy dir %s: %w", p, err)
			}
		} else {
			if err := copyFile(p, destPath); err != nil {
				return "", fmt.Errorf("failed to copy file %s: %w", p, err)
			}
		}
	}

	// 4. Generate EVIDENCE_VERSION
	if err := os.WriteFile(filepath.Join(stagingDir, "EVIDENCE_VERSION"), []byte("v1\n"), 0644); err != nil {
		return "", fmt.Errorf("failed to write EVIDENCE_VERSION: %w", err)
	}

	// 5. Generate MANIFEST.tsv
	manifestLines, err := generateManifest(dataDir)
	if err != nil {
		return "", fmt.Errorf("failed to generate manifest: %w", err)
	}
	manifestPath := filepath.Join(stagingDir, "MANIFEST.tsv")
	if err := os.WriteFile(manifestPath, []byte(strings.Join(manifestLines, "\n")+"\n"), 0644); err != nil {
		return "", fmt.Errorf("failed to write MANIFEST.tsv: %w", err)
	}

	// 6. Generate METADATA.json
	gitInfo := getGitInfo()
	meta := Metadata{
		Contract:        "evidence-pack-v1",
		ContractVersion: 1,
		CreatedAtUTC:    cfg.Timestamp.Format(time.RFC3339),
		Kind:            cfg.Kind,
		Git:             gitInfo,
		PayloadRoot:     "data/",
		Tool:            ToolInfo{Name: "evidencepack", Lang: "go"},
	}
	metaBytes, err := json.MarshalIndent(meta, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal metadata: %w", err)
	}
	// Append newline for POSIX niceness
	metaBytes = append(metaBytes, '\n')
	if err := os.WriteFile(filepath.Join(stagingDir, "METADATA.json"), metaBytes, 0644); err != nil {
		return "", fmt.Errorf("failed to write METADATA.json: %w", err)
	}

	// 7. Generate CHECKSUMS.sha256
	checksums, err := calculateRootChecksums(stagingDir)
	if err != nil {
		return "", fmt.Errorf("failed to calculate checksums: %w", err)
	}
	if err := os.WriteFile(filepath.Join(stagingDir, "CHECKSUMS.sha256"), []byte(checksums), 0644); err != nil {
		return "", fmt.Errorf("failed to write CHECKSUMS.sha256: %w", err)
	}

	// 8. Create Tarball (Deterministic)
	// Output filename: evidence_<kind>_<UTC>_<gitsha7>.tar.gz
	shortSha := gitInfo.SHA
	if len(shortSha) > 7 {
		shortSha = shortSha[:7]
	}
	if shortSha == "" {
		shortSha = "nosha"
	}
	tsStr := cfg.Timestamp.Format("20060102T150405.000000000Z")
	tarName := fmt.Sprintf("evidence_%s_%s_%s.tar.gz", cfg.Kind, tsStr, shortSha)

	// Ensure store packs dir exists
	packsDir := filepath.Join(cfg.StoreDir, "packs", cfg.Kind)
	if err := os.MkdirAll(packsDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create packs dir: %w", err)
	}

	tarPath := filepath.Join(packsDir, tarName)
	// We write to a tmp file specific to the target first, then rename?
	// Or write directly since we are creating a new file.
	// Safer to write to tmp then move.
	tmpTarPath := filepath.Join(filepath.Join(cfg.StoreDir, "tmp"), tarName)

	if err := createDeterministicTar(stagingDir, tmpTarPath); err != nil {
		return "", fmt.Errorf("failed to create tar: %w", err)
	}

	// 9. Atomic Move
	if err := os.Rename(tmpTarPath, tarPath); err != nil {
		return "", fmt.Errorf("failed to move tar to store: %w", err)
	}

	// 10. Update Index
	indexDir := filepath.Join(cfg.StoreDir, "index")
	if err := os.MkdirAll(indexDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create index dir: %w", err)
	}
	indexPath := filepath.Join(indexDir, "packs.tsv")

	// Calculate final tar hash and size for index
	tarHash, tarSize, err := fileSha256AndSize(tarPath)
	if err != nil {
		return "", fmt.Errorf("failed to hash tar: %w", err)
	}

	// Columns: created_at_utc, kind, filename, git_sha, sha256, size
	entry := fmt.Sprintf("%s\t%s\t%s\t%s\t%s\t%d\n",
		cfg.Timestamp.Format(time.RFC3339),
		cfg.Kind,
		tarName,
		gitInfo.SHA,
		tarHash,
		tarSize,
	)

	f, err := os.OpenFile(indexPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return "", fmt.Errorf("failed to open index: %w", err)
	}
	defer f.Close()
	if _, err := f.WriteString(entry); err != nil {
		return "", fmt.Errorf("failed to write index: %w", err)
	}

	fmt.Printf("Created evidence pack: %s\n", tarPath)
	return tarPath, nil
}

// Helpers

func copyFile(src, dst string) error {
	s, err := os.Open(src)
	if err != nil {
		return err
	}
	defer s.Close()

	if err := checkSymlink(src); err != nil {
		return err
	}

	d, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer d.Close()

	_, err = io.Copy(d, s)
	return err
}

func copyDir(src, dst string) error {
	if err := checkSymlink(src); err != nil {
		return err
	}
	if err := os.MkdirAll(dst, 0755); err != nil {
		return err
	}
	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())
		if entry.IsDir() {
			if err := copyDir(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := copyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}
	return nil
}

func checkSymlink(path string) error {
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("symlinks are prohibited: %s", path)
	}
	return nil
}

func generateManifest(dataDir string) ([]string, error) {
	var lines []string
	err := filepath.Walk(dataDir, func(path string, info os.FileInfo, err error) error {
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
		// Assuming data/ is root for manifest paths.
		// Normalized path separator
		relPath = filepath.ToSlash(relPath)

		hash, size, err := fileSha256AndSize(path)
		if err != nil {
			return err
		}
		// path, sha256, size
		lines = append(lines, fmt.Sprintf("%s\t%s\t%d", relPath, hash, size))
		return nil
	})
	sort.Strings(lines)
	return lines, err
}

func calculateRootChecksums(dir string) (string, error) {
	files := []string{"EVIDENCE_VERSION", "METADATA.json", "MANIFEST.tsv"}
	var result strings.Builder
	for _, fname := range files {
		path := filepath.Join(dir, fname)
		hash, _, err := fileSha256AndSize(path)
		if err != nil {
			return "", err
		}
		result.WriteString(fmt.Sprintf("%s  %s\n", hash, fname)) // Standard sha256sum format
	}
	return result.String(), nil
}

func fileSha256AndSize(path string) (string, int64, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", 0, err
	}
	defer f.Close()

	h := sha256.New()
	size, err := io.Copy(h, f)
	if err != nil {
		return "", 0, err
	}
	return hex.EncodeToString(h.Sum(nil)), size, nil
}

func getGitInfo() GitInfo {
	shaCmd := exec.Command("git", "rev-parse", "HEAD")
	shaOut, err := shaCmd.Output()
	sha := strings.TrimSpace(string(shaOut))
	if err != nil {
		sha = ""
	}

	dirtyCmd := exec.Command("git", "status", "--porcelain")
	dirtyOut, _ := dirtyCmd.Output()
	dirty := len(dirtyOut) > 0

	return GitInfo{SHA: sha, Dirty: dirty}
}

func createDeterministicTar(srcDir, tarPath string) error {
	tf, err := os.Create(tarPath)
	if err != nil {
		return err
	}
	defer tf.Close()

	gw := gzip.NewWriter(tf)
	defer gw.Close()

	tw := tar.NewWriter(gw)
	defer tw.Close()

	// Walk and Collect all files to sort them
	type item struct {
		path string
		info os.FileInfo
	}
	var items []item

	err = filepath.Walk(srcDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		// Don't include the root dir itself in the list if it matches srcDir
		if path == srcDir {
			return nil
		}
		items = append(items, item{path: path, info: info})
		return nil
	})
	if err != nil {
		return err
	}

	// Sort lexicographically by relative path
	sort.Slice(items, func(i, j int) bool {
		relI, _ := filepath.Rel(srcDir, items[i].path)
		relJ, _ := filepath.Rel(srcDir, items[j].path)
		return relI < relJ
	})

	for _, it := range items {
		relPath, err := filepath.Rel(srcDir, it.path)
		if err != nil {
			return err
		}

		header, err := tar.FileInfoHeader(it.info, "")
		if err != nil {
			return err
		}

		// Determinism overrides
		header.Name = filepath.ToSlash(relPath)
		header.ModTime = time.Unix(0, 0) // Epoch 0
		header.Uid = 0
		header.Gid = 0
		header.Uname = ""
		header.Gname = ""
		header.AccessTime = time.Unix(0, 0)
		header.ChangeTime = time.Unix(0, 0)

		if err := tw.WriteHeader(header); err != nil {
			return err
		}

		if !it.info.IsDir() {
			f, err := os.Open(it.path)
			if err != nil {
				return err
			}
			if _, err := io.Copy(tw, f); err != nil {
				f.Close()
				return err
			}
			f.Close()
		}
	}
	return nil
}
