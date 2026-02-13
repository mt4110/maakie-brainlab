package reviewpack

import (
	"bytes"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/crypto/openpgp"
	"golang.org/x/crypto/openpgp/armor"
)

func runPack(args []string) {
	defer logPhase("runPack")()
	tarFile := packToTar(args)
	fmt.Printf("[OK] created %s\n", tarFile)
}

func packToTar(args []string) string {
	defer logPhase("packToTar")()
	fs := flag.NewFlagSet("pack", flag.ExitOnError)

	timebox := fs.Int("timebox", defaultTimeboxSec, "Timebox in seconds")
	skipEval := fs.Bool("skip-eval", false, "Skip make run-eval")
	signKey := fs.String("sign-key", "", "Path to private key for signing")
	fs.Parse(args)

	repoRoot := resolveRepoRoot()

	// Environment overrides
	if os.Getenv("TIMEBOX_SEC") != "" {
		fmt.Sscanf(os.Getenv("TIMEBOX_SEC"), "%d", timebox)
	}
	if os.Getenv("SKIP_EVAL") == "1" {
		*skipEval = true
	}

	// Setup
	timestamp := time.Now().Format("20060102_150405")
	packName := fmt.Sprintf("%s_%s", packPrefix, timestamp)
	packDir, cleanup := setupPackDir(packName)
	defer cleanup()

	fmt.Printf("=== review_pack (S4 Hardened) ===\nTarget : %s%s\nTimebox: %ds\nWork   : %s\n", packName, extTarGz, *timebox, packDir)

	// 1. Preflight
	runPreflightChecks(repoRoot, packDir, timestamp, *timebox, *skipEval, "legacy", false)

	nCommits := "5"
	if fs.NArg() > 0 {
		nCommits = fs.Arg(0)
	}
	collectGitInfo(repoRoot, packDir, nCommits)

	// 2. Secrets Scan
	scanSecrets(packDir)

	runMake(packDir, fileMakeTest, []string{"make", "test"}, *timebox, 4)

	// 4. Make Run-Eval
	if !*skipEval {
		runMake(packDir, fileMakeEval, []string{"make", "run-eval"}, *timebox, 5)
	} else {
		skipPath := filepath.Join(packDir, fileMakeEval)
		if err := os.WriteFile(skipPath, []byte("SKIP_EVAL set.\n"), 0644); err != nil {
			log.Fatalf(msgFatalWrite, skipPath, err)
		}
	}

	snapshotDir := filepath.Join(packDir, dirSrcSnapshot)
	if err := ensureDir(snapshotDir); err != nil {
		log.Fatalf("[FATAL] %v", err)
	}
	for _, f := range listTrackedFiles() {
		copyFile(f, filepath.Join(snapshotDir, f))
	}

	if !*skipEval {
		abs, _, err := findLatestEvalResult(repoRoot)
		if err == nil {
			copyEvalAsLatest(snapshotDir, abs)
		} else {
			log.Printf("[WARN] No eval result found to bundle: %v", err)
		}
	} else {
		// If skipped, we might not have one. S4 legacy didn't demand it strictly?
		// Actually Gate-1 demands it. If skipped, we try to find existing.
		abs, _, err := findLatestEvalResult(repoRoot)
		if err == nil {
			copyEvalAsLatest(snapshotDir, abs)
		}
	}

	// 6. Documentation & Specifications
	writeVersionAndSpec(packDir)
	writeReadme(packDir)
	writeVerifyScript(packDir)
	kindPath := filepath.Join(packDir, "review_pack_v1")
	if err := os.WriteFile(kindPath, []byte("1\n"), 0644); err != nil {
		log.Fatalf(msgFatalWrite, kindPath, err)
	}

	// 7. Self-Verify
	runSelfVerify(packDir)

	// 8-11. Finalize
	tarFile := finalizePack(packDir, packName, "review_bundle")

	// Signing
	if *signKey != "" {
		if err := signFile(*signKey, tarFile); err != nil {
			log.Fatalf("[FATAL] Signing failed: %v", err)
		}
	}

	// Legacy Copy
	legacyName := strings.Replace(packName, "review_bundle", "review_pack", 1) + extTarGz
	copyFile(tarFile, legacyName)
	fmt.Printf("[INFO] Created legacy copy: %s\n", legacyName)

	return tarFile
}

func finalizePack(packDir, packName, bundleName string) string {
	filesToPack := generatePackFilelist(packDir)

	createManifest(packDir, filesToPack)

	createChecksums(packDir)

	tarFile := packName + extTarGz
	finalFileList := generatePackFilelist(packDir)
	createDeterministicTar(packDir, finalFileList, bundleName, tarFile)
	return tarFile
}

func signFile(keyPath, targetPath string) error {
	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return fmt.Errorf("read key: %w", err)
	}

	block, err := armor.Decode(bytes.NewReader(keyBytes))
	if err != nil {
		return fmt.Errorf("decode armor: %w", err)
	}
	if block.Type != openpgp.PrivateKeyType {
		return fmt.Errorf("invalid key type: %s", block.Type)
	}

	entityList, err := openpgp.ReadKeyRing(block.Body)
	if err != nil {
		return fmt.Errorf("read keyring: %w", err)
	}
	signer := entityList[0]

	// Read Target
	targetBytes, err := os.ReadFile(targetPath)
	if err != nil {
		return fmt.Errorf("read target: %w", err)
	}

	// Create Signature
	sigBuf := new(bytes.Buffer)
	if err := openpgp.ArmoredDetachSign(sigBuf, signer, bytes.NewReader(targetBytes), nil); err != nil {
		return fmt.Errorf("signing: %w", err)
	}

	outPath := targetPath + ".asc"
	if err := os.WriteFile(outPath, sigBuf.Bytes(), 0644); err != nil {
		return fmt.Errorf("write sig: %w", err)
	}
	fmt.Printf("[Sign] Signed %s -> %s\n", targetPath, outPath)
	return nil
}
