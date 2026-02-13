package reviewpack

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func runSubmit(args []string) {
	fmt.Println("=== SUBMIT (strict / verify-only) ===")

	fs := flag.NewFlagSet("submit", flag.ExitOnError)
	timebox := fs.Int("timebox", defaultTimeboxSec, "Timebox in seconds")
	// Deprecated: existing skip-eval for pack, but for submit we use mode
	_ = fs.Bool("skip-eval", false, "Deprecated: use --mode verify-only")
	mode := fs.String("mode", "strict", "submit mode: strict | verify-only")
	skipTest := fs.Bool("skip-test", false, "skip tests during submission")
	// nCommits positional
	fs.Parse(args)

	if *mode != "strict" && *mode != "verify-only" {
		log.Fatalf("[FATAL] Invalid mode: %s (must be strict or verify-only)", *mode)
	}

	if *skipTest && *mode == "strict" {
		log.Fatalf("[FATAL] --skip-test is only permitted in --mode verify-only")
	}

	// 1. Pack with mode-specific logic
	tarFile := packToTarForSubmit(fs.Args(), *timebox, *mode, *skipTest)
	packSha, err := fileSha256(tarFile)
	if err != nil {
		log.Fatalf("[FATAL] sha256(%s): %v", tarFile, err)
	}
	fmt.Printf("PACK:   %s\nSHA256: %s\n", tarFile, packSha)

	// Verification Phase
	tmpDir, err := os.MkdirTemp("", "reviewpack-verify-*")
	if err != nil {
		log.Fatalf(msgFatalMkdirTemp, "reviewpack-verify-*", err)
	}
	defer os.RemoveAll(tmpDir)

	extractTar(tarFile, tmpDir)

	// Find the root (fixed internal name or timestamped name check)
	// We know createDeterministicTar uses "review_pack" as internal root.
	root := filepath.Join(tmpDir, "review_pack")
	if _, err := os.Stat(root); os.IsNotExist(err) {
		// Fallback: try to find it
		r, err := findDirContainingFile(tmpDir, "PACK_VERSION", 2)
		if err != nil {
			log.Fatalf("[FATAL] Could not find pack root: %v", err)
		}
		root = r
	}

	fmt.Println("=== CHECK: checksums + verify (host) ===")
	runVerify([]string{root})

	fmt.Println("=== CHECK: Gate-1 verify-only (pack-contained) ===")
	// Gate-1 verify-only is called by VERIFY.sh usually, but we call it explicitly here for double check
	runCmd(filepath.Join(root, "src_snapshot"), "bash", "ops/gate1.sh", "--verify-only")

	fmt.Println("OK: verified ✅")
	fmt.Printf("SUBMIT: %s\n", tarFile)
	fmt.Printf("SHA256: %s\n", packSha)
}

func packToTarForSubmit(args []string, timebox int, mode string, skipTest bool) string {
	defer logPhase("packToTarForSubmit")()

	repoRoot := resolveRepoRoot()

	// Environment overrides
	if os.Getenv("TIMEBOX_SEC") != "" {
		fmt.Sscanf(os.Getenv("TIMEBOX_SEC"), "%d", &timebox)
	}

	skipEval := (mode == "verify-only")

	// Setup
	timestamp := time.Now().Format("20060102_150405")
	packName := fmt.Sprintf("%s_%s", packPrefix, timestamp)
	packDir, cleanup := setupPackDir(packName)
	defer cleanup()

	fmt.Printf("=== review_pack (S7 Run Always) ===\nTarget : %s%s\nTimebox: %ds\nMode   : %s\nWork   : %s\n", packName, extTarGz, timebox, mode, packDir)

	// 1. Preflight
	os.Setenv("PYTHONWARNINGS", "ignore::DeprecationWarning")
	runPreflightChecks(repoRoot, packDir, timestamp, timebox, skipEval, mode, skipTest)

	nCommits := "5"
	if len(args) > 0 {
		nCommits = args[0]
	}
	collectGitInfo(repoRoot, packDir, nCommits)

	scanSecrets(packDir)

	// 3. Make Test
	if !skipTest {
		testCmd := []string{"make", "test"}
		if mode == "strict" {
			testCmd = []string{"make", "ci-test"}
		}
		runMake(packDir, fileMakeTest, testCmd, timebox, 4)
	} else {
		fmt.Println("[INFO] skip-test is active: skipping make test")
		if err := generatePlaceholderLog(packDir); err != nil {
			log.Fatalf("[FATAL] %v", err)
		}
	}

	// 4. Make Run-Eval (Unified Flow)
	var selectedEvalAbs, selectedEvalRel string
	var selectedEvalSha string
	var selectedEvalBytes int64

	if mode == "strict" {
		// Strict: Run eval, fail if fails
		runMake(packDir, fileMakeEval, []string{"make", "run-eval"}, timebox, 5)

		// After run, find the result
		abs, rel, err := findLatestEvalResult(repoRoot)
		if err != nil {
			log.Fatalf("[FATAL] strict mode: failed to find generated eval result: %v", err)
		}
		selectedEvalAbs, selectedEvalRel = abs, rel

		if err := validateJsonlLooksOk(selectedEvalAbs); err != nil {
			log.Fatalf("[FATAL] strict mode: generated result %s is invalid: %v", selectedEvalRel, err)
		}

		// Append selection info to log
		f, err := os.OpenFile(filepath.Join(packDir, fileMakeEval), os.O_APPEND|os.O_WRONLY, 0644)
		if err == nil {
			fmt.Fprintf(f, "\n[S7] Selected Result: %s\n", selectedEvalRel)
			f.Close()
		}

	} else {
		// Verify-only: Find latest existing result
		abs, rel, err := findLatestEvalResult(repoRoot)
		if err != nil {
			log.Printf("[FATAL] verify-only mode requires valid eval/results/*.jsonl (excluding latest.jsonl): %v", err)
			log.Printf("[HINT] run strict once to generate result: go run cmd/reviewpack/main.go submit")
			log.Printf("[HINT] or run self-hosted eval workflow (eval_strict.yml)")
			log.Printf("[HINT] or run local seed (fastest): make seed-eval")
			os.Exit(5)
		}
		selectedEvalAbs, selectedEvalRel = abs, rel

		if err := validateJsonlLooksOk(selectedEvalAbs); err != nil {
			log.Printf("[FATAL] verify-only mode: selected result %s is invalid: %v", selectedEvalRel, err)
			os.Exit(5)
		}

		// Calculate stats for skip log (and meta later)
		sha, err := fileSha256(selectedEvalAbs)
		if err != nil {
			log.Fatalf(msgFatalSha256, selectedEvalRel, err)
		}
		st, err := os.Stat(selectedEvalAbs)
		if err != nil {
			log.Fatalf(msgFatalStat, selectedEvalRel, err)
		}
		selectedEvalSha = sha
		selectedEvalBytes = st.Size()

		// Write SKIP log
		logContent := fmt.Sprintf("mode=%s\nreason=reuse_latest_timestamp\nselected_result=%s\nselected_sha256=%s\nselected_bytes=%d\n",
			mode, selectedEvalRel, selectedEvalSha, selectedEvalBytes)
		if err := os.WriteFile(filepath.Join(packDir, fileMakeEval), []byte(logContent), 0644); err != nil {
			log.Fatalf("[FATAL] write skip log: %v", err)
		}

		fmt.Printf("[INFO] verify-only: reusing %s (sha=%s)\n", selectedEvalRel, selectedEvalSha)
	}

	// 5. Source Snapshot & Bundle Eval Result
	log.Println("DEBUG: Creating src_snapshot...")
	snapshotDir := filepath.Join(packDir, dirSrcSnapshot)
	if err := ensureDir(snapshotDir); err != nil {
		log.Fatalf("[FATAL] %v", err)
	}
	for _, f := range listTrackedFiles() {
		copyFile(f, filepath.Join(snapshotDir, f))
	}
	// Copy selected result as latest.jsonl
	resultSha, resultBytes, _, err := copyEvalAsLatest(snapshotDir, selectedEvalAbs)
	if err != nil {
		log.Fatalf("[FATAL] copyEvalAsLatest: %v", err)
	}

	// If strict, we didn't calculate source sha/bytes yet, do it now
	if selectedEvalSha == "" {
		s, err := fileSha256(selectedEvalAbs)
		if err != nil {
			log.Fatalf(msgFatalSha256, selectedEvalRel, err)
		}
		selectedEvalSha = s
		fi, _ := os.Stat(selectedEvalAbs)
		selectedEvalBytes = fi.Size()
	}

	// Verify copy integrity
	if selectedEvalSha != resultSha {
		log.Fatalf("[FATAL] Integrity error: source sha (%s) != snapshot sha (%s)", selectedEvalSha, resultSha)
	}

	// Write Meta (S7-20 Unified)
	writeMeta(packDir, timestamp, timebox, skipEval, mode, skipTest,
		resultSha, resultBytes,
		selectedEvalRel, selectedEvalSha, selectedEvalBytes)

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

	// Legacy Copy
	legacyName := strings.Replace(packName, "review_bundle", "review_pack", 1) + extTarGz
	copyFile(tarFile, legacyName)
	fmt.Printf("[INFO] Created legacy copy: %s\n", legacyName)

	return tarFile
}

func checkLatestJsonlForVerifyOnly(repoRoot string) error {
	path := filepath.Join(repoRoot, fileLatestJsonl)
	info, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("file not found: %s", path)
		}
		return err
	}
	if info.Size() == 0 {
		return fmt.Errorf("file is empty: %s", path)
	}
	// Check if it looks like JSONL (read first line)
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	if scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if len(line) > 0 && !strings.HasPrefix(line, "{") {
			return fmt.Errorf("first line does not look like JSON: %s...", line[:min(len(line), 20)])
		}
	} else {
		if err := scanner.Err(); err != nil {
			return err
		}
		return fmt.Errorf("file contains no readable lines")
	}
	return nil
}
