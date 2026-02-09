package reviewpack
// ... (Full content of original main.go, but with package reviewpack and Run entry point)
import (
	"archive/tar"
	"bufio"
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"syscall"
	"time"

	"golang.org/x/crypto/openpgp"
	"golang.org/x/crypto/openpgp/armor"
)

const (
	defaultTimeboxSec = 300
	packPrefix        = "review_bundle"

	// Constants for logging and filenames
	msgFatalMkdirTemp  = "[FATAL] MkdirTemp: %v"
	msgFatalMkdirAll   = "[FATAL] MkdirAll: %v"
	msgDebugPreflight  = "DEBUG: Starting preflight checks..."
	msgFatalGitStatus  = "[FATAL] git status --porcelain failed: %v"
	msgFatalSha256     = "[FATAL] sha256 %s: %v"
	msgFatalStat       = "[FATAL] stat %s: %v"
	fileStatus         = "01_status.txt"
	fileGitLog         = "10_git_log.txt"
	fileGitDiff        = "11_git_diff.patch"
	fileMakeTest       = "30_make_test.log"
	fileMakeEval       = "31_make_run_eval.log"
	fileSelfVerify     = "40_self_verify.log"
	fileManifest       = "MANIFEST.tsv"
	fileChecksums      = "CHECKSUMS.sha256"
	filePackVersion    = "PACK_VERSION"
	fileSpec           = "SPEC.md"
	fileLatestJsonl    = "eval/results/latest.jsonl"
	extTarGz           = ".tar.gz"
	dirSrcSnapshot     = "src_snapshot"
	dirEvalResults     = "eval/results"

	// Refactoring Constants
	msgFatalCreate = "[FATAL] create %s: %v"
	msgFatalMkdir  = "[FATAL] mkdir %s: %v"
	msgFatalWrite  = "[FATAL] write %s: %v"
	codeBlockBash  = "```bash"
)

// Run is the main entry point for the reviewpack tool.
func Run(args []string) int {
	if len(args) < 2 {
		usage()
		return 1
	}

	subCmd := args[1]
	cmdArgs := args[2:]

	switch subCmd {
	case "pack":
		runPack(cmdArgs)
	case "submit":
		runSubmit(cmdArgs)
	case "verify":
		runVerify(cmdArgs)
	case "repro-check":
		runReproCheck(cmdArgs)
	default:
		usage()
		return 1
	}
	return 0
}

func usage() {
	fmt.Fprintf(os.Stderr, "Usage: reviewpack <command> [args]\n")
	fmt.Fprintf(os.Stderr, "Commands:\n")
	fmt.Fprintf(os.Stderr, "  pack [--timebox N] [--skip-eval] [N_COMMITS]\n")
	fmt.Fprintf(os.Stderr, "  submit [--timebox N] [--mode strict|verify-only] [N_COMMITS]\n")
	fmt.Fprintf(os.Stderr, "  verify <dir|tar.gz>\n")
	fmt.Fprintf(os.Stderr, "  repro-check\n")
}

// resolveRepoRoot ensures we are inside the repo and returns the root path.
func resolveRepoRoot() string {
	// Try Getwd first
	if _, err := os.Getwd(); err != nil {
		log.Fatalf("[FATAL] Getwd: %v", err)
	}

	out, err := exec.Command("git", "rev-parse", "--show-toplevel").Output()
	if err != nil {
		log.Fatalf("[FATAL] git rev-parse --show-toplevel failed: %v", err)
	}
	root := strings.TrimSpace(string(out))
	if root == "" {
		log.Fatalf("[FATAL] git rev-parse --show-toplevel returned empty")
	}
	if err := os.Chdir(root); err != nil {
		log.Fatalf("[FATAL] chdir to repo root failed: %v", err)
	}
	return root
}

// --- PACK ---

func logPhase(name string) func() {
	start := time.Now()
	log.Printf("[PHASE_START] %s", name)
	return func() {
		log.Printf("[PHASE_END]   %s (%v)", name, time.Since(start))
	}
}

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
	runPreflightChecks(repoRoot, packDir, timestamp, *timebox, *skipEval, "legacy")

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
		_ = os.WriteFile(filepath.Join(packDir, fileMakeEval), []byte("SKIP_EVAL set.\n"), 0644)
	}

	snapshotDir := filepath.Join(packDir, dirSrcSnapshot)
	if err := os.MkdirAll(snapshotDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdirAll, err)
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
	_ = os.WriteFile(filepath.Join(packDir, "review_pack_v1"), []byte("1\n"), 0644)

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

func packToTarForSubmit(args []string, timebox int, mode string) string {
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
	runPreflightChecks(repoRoot, packDir, timestamp, timebox, skipEval, mode)

	nCommits := "5"
	if len(args) > 0 {
		nCommits = args[0]
	}
	collectGitInfo(repoRoot, packDir, nCommits)

	scanSecrets(packDir)

	// 3. Make Test
	runMake(packDir, fileMakeTest, []string{"make", "test"}, timebox, 4)

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
	if err := os.MkdirAll(snapshotDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdirAll, err)
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
	writeMeta(packDir, timestamp, timebox, skipEval, mode, 
		resultSha, resultBytes, 
		selectedEvalRel, selectedEvalSha, selectedEvalBytes)

	// 6. Documentation & Specifications
	writeVersionAndSpec(packDir)
	writeReadme(packDir)
	writeVerifyScript(packDir)
	_ = os.WriteFile(filepath.Join(packDir, "review_pack_v1"), []byte("1\n"), 0644)

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

// --- SUBMIT (pack + verify-only) ---
func runSubmit(args []string) {
	fmt.Println("=== SUBMIT (strict / verify-only) ===")

	fs := flag.NewFlagSet("submit", flag.ExitOnError)
	timebox := fs.Int("timebox", defaultTimeboxSec, "Timebox in seconds")
	// Deprecated: existing skip-eval for pack, but for submit we use mode
	_ = fs.Bool("skip-eval", false, "Deprecated: use --mode verify-only")
	mode := fs.String("mode", "strict", "submit mode: strict | verify-only")
	// nCommits positional
	fs.Parse(args)

	if *mode != "strict" && *mode != "verify-only" {
		log.Fatalf("[FATAL] Invalid mode: %s (must be strict or verify-only)", *mode)
	}

	// 1. Pack with mode-specific logic
	tarFile := packToTarForSubmit(fs.Args(), *timebox, *mode)
	packSha, err := fileSha256(tarFile)
	if err != nil {
		log.Fatalf("[FATAL] sha256(%s): %v", tarFile, err)
	}
	fmt.Printf("PACK:   %s\nSHA256: %s\n", tarFile, packSha)

	// Verification Phase
	tmpDir, err := os.MkdirTemp("", "reviewpack-verify-*")
	if err != nil {
		log.Fatalf(msgFatalMkdirTemp, err)
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

// --- HELPERS (S4 Hardened) ---

func generatePackFilelist(dir string) []string {
	walker := &packWalker{
		dir: dir,
	}
	if err := filepath.WalkDir(dir, walker.walk); err != nil {
		log.Fatalf("[FATAL] WalkDir %s: %v", dir, err)
	}

	if len(walker.violations) > 0 {
		log.Printf("[FATAL] Contamination checks failed (%d violations):", len(walker.violations))
		for _, v := range walker.violations {
			log.Printf("  - %s", v)
		}
		os.Exit(1)
	}

	// Deterministic Order (S4-04-01)
	sort.Strings(walker.files)
	return walker.files
}

type packWalker struct {
	dir        string
	files      []string
	violations []string
}

func (w *packWalker) walk(path string, d fs.DirEntry, walkErr error) error {
	if walkErr != nil {
		return walkErr
	}
	if d.IsDir() {
		if isProhibitedDir(filepath.Base(path)) {
			return fs.SkipDir
		}
		return nil
	}

	rel, err := filepath.Rel(w.dir, path)
	if err != nil {
		return err
	}

	if msg := checkProhibitedFile(filepath.Base(path), rel); msg != "" {
		w.violations = append(w.violations, msg)
	}

	if msg, err := checkSymlink(d, rel); err != nil {
		return err
	} else if msg != "" {
		w.violations = append(w.violations, msg)
	}

	checkLargeFile(d, rel)

	w.files = append(w.files, rel)
	return nil
}

func isProhibitedDir(base string) bool {
	return base == ".git" || base == "node_modules" || base == "target" || base == "__pycache__" || base == ".local"
}

func checkProhibitedFile(base, rel string) string {
	// 1. Names
	if base == ".DS_Store" || base == ".env" || strings.HasSuffix(base, ".pem") || strings.HasPrefix(base, "id_rsa") || strings.HasSuffix(base, ".swp") || strings.HasSuffix(base, "~") {
		return fmt.Sprintf("Prohibited file: %s", rel)
	}
	if strings.HasSuffix(base, ".log") {
		// Whitelist generated evidence logs
		if base != "30_make_test.log" && base != "31_make_run_eval.log" && base != "40_self_verify.log" {
			return fmt.Sprintf("Prohibited file: %s", rel)
		}
	}
	return ""
}

func checkSymlink(d fs.DirEntry, rel string) (string, error) {
	info, err := d.Info()
	if err != nil {
		return "", err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return fmt.Sprintf("Symlink detected: %s", rel), nil
	}
	return "", nil
}

func checkLargeFile(d fs.DirEntry, rel string) {
	info, _ := d.Info() // Error handling omitted as we strictly called it in checkSymlink or can separate
	if info.Size() > 20*1024*1024 {
		log.Printf("[WARN] Large file: %s (%.2f MB)", rel, float64(info.Size())/1024/1024)
	}
}

func writeVersionAndSpec(dir string) {
	// S4-05
	_ = os.WriteFile(filepath.Join(dir, "PACK_VERSION"), []byte("1\n"), 0644)

	spec := `# Reviewpack Specification (v1)

## 0. Philosophy
This pack is a self-contained, deterministic, and verifiable artifact.
It guarantees that "Same Input -> Same Output" (Checksums match).

## 1. Structure
- VERIFY.sh: Entry point for verification.
- CHECKSUMS.sha256: Definition of Integrity. Includes MANIFEST.tsv.
- MANIFEST.tsv: Human-readable file list (Path, SHA256, Bytes).
- PACK_VERSION: Semantic version of this pack format.
- src_snapshot/: The actual content.

## 2. Determinism
- Archives are tar.gz.
- Tar headers have ModTime=0, Uid/Gid=0.
- Gzip headers have ModTime=0, Name="", OS=Unknown.
- File order is strictly sorted by path.
- Content hash (CHECKSUMS.sha256) is the single source of truth.

## 3. Verification
Run ./VERIFY.sh to validate integrity.
`
	_ = os.WriteFile(filepath.Join(dir, "SPEC.md"), []byte(spec), 0644)
}

func createManifest(dir string, files []string) {
	// S4-01, S4-02
	manifestPath := filepath.Join(dir, fileManifest)
	manFile, err := os.Create(manifestPath)
	if err != nil {
		log.Fatalf(msgFatalCreate, manifestPath, err)
	}
	// Header
	fmt.Fprintln(manFile, "path\tsha256\tbytes")

	for _, rel := range files {
		// Skip MANIFEST.tsv itself if it happens to be in list
		if rel == fileManifest {
			continue
		}
		abs := filepath.Join(dir, rel)
		h, err := fileSha256(abs)
		if err != nil {
			log.Fatalf(msgFatalSha256, abs, err)
		}
		st, err := os.Stat(abs)
		if err != nil {
			log.Fatalf(msgFatalStat, abs, err)
		}
		fmt.Fprintf(manFile, "%s\t%s\t%d\n", rel, h, st.Size())
	}

	// Critical Fix (S4-01): Explicit Close before returning/hashing
	if err := manFile.Close(); err != nil {
		log.Fatalf(msgFatalSha256, fileManifest, err)
	}
}

func createChecksums(dir string) {
	// S4-03
	// Regenerate list to include MANIFEST.tsv, SPEC.md, etc.
	files := generatePackFilelist(dir) // This is sorted

	var lines []string
	for _, rel := range files {
		if rel == fileChecksums {
			continue
		}
		abs := filepath.Join(dir, rel)
		h, err := fileSha256(abs)
		if err != nil {
			log.Fatalf(msgFatalSha256, abs, err)
		}
		lines = append(lines, fmt.Sprintf("%s  %s", h, rel))
	}
	// Write
	out := filepath.Join(dir, fileChecksums)
	if err := os.WriteFile(out, []byte(strings.Join(lines, "\n")+"\n"), 0644); err != nil {
		log.Fatalf("[FATAL] write checksums: %v", err)
	}
}

func createDeterministicTar(srcDir string, fileList []string, rootName string, outTarGz string) {
	// S4-04
	f, err := os.Create(outTarGz)
	if err != nil {
		log.Fatalf("[FATAL] create tar: %v", err)
	}
	defer f.Close()

	gw := gzip.NewWriter(f)
	gw.Name = ""
	gw.Comment = ""
	gw.ModTime = time.Unix(0, 0)
	gw.OS = 255 // Unknown
	defer gw.Close()

	tw := tar.NewWriter(gw)
	defer tw.Close()

	for _, rel := range fileList {
		abs := filepath.Join(srcDir, rel)
		info, err := os.Lstat(abs)
		if err != nil {
			log.Fatalf("[FATAL] lstat %s: %v", abs, err)
		}

		// Create header
		linkTarget := ""
		if info.Mode()&os.ModeSymlink != 0 {
			linkTarget, _ = os.Readlink(abs)
		}

		hdr, err := tar.FileInfoHeader(info, linkTarget)
		if err != nil {
			log.Fatalf("[FATAL] tar header: %v", err)
		}

		// Normalize Header (S4-04-03)
		hdr.Name = filepath.ToSlash(filepath.Join(rootName, rel))
		hdr.ModTime = time.Unix(0, 0)
		hdr.AccessTime = time.Unix(0, 0)
		hdr.ChangeTime = time.Unix(0, 0)
		hdr.Uid = 0
		hdr.Gid = 0
		hdr.Uname = ""
		hdr.Gname = ""
		hdr.Format = tar.FormatPAX

		if err := tw.WriteHeader(hdr); err != nil {
			log.Fatalf("[FATAL] write header %s: %v", rel, err)
		}

		if info.Mode().IsRegular() {
			data, err := os.Open(abs)
			if err != nil {
				log.Fatalf("[FATAL] open %s: %v", abs, err)
			}
			if _, err := io.Copy(tw, data); err != nil {
				data.Close()
				log.Fatalf("[FATAL] copy content %s: %v", abs, err)
			}
			data.Close()
		}
	}
}

// --- VERIFY ---

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
		rel, _ := filepath.Rel(verifyRoot, path)
		if rel == "CHECKSUMS.sha256" {
			return nil
		}
		if !validFiles[rel] {
			extraFiles = append(extraFiles, rel)
		}
		return nil
	})
	if err != nil {
		log.Fatalf("[FAIL] WalkDir: %v", err)
	}

	if len(extraFiles) > 0 {
		log.Printf("[FAIL] Extra files detected (not in CHECKSUMS.sha256):")
		sort.Strings(extraFiles)
		for _, f := range extraFiles {
			log.Printf("  - %s", f)
		}
		os.Exit(11)
	}

	fmt.Println("=== ALL PASS ===")
	fmt.Println("=== ALL PASS ===")
}

// --- SIGNING (S7-01) ---

// signFile creates a detached armored signature for the target file using the private key at privKeyPath.
// It creates <targetPath>.asc
func signFile(privKeyPath, targetPath string) error {
	// Read Private Key
	keyBytes, err := os.ReadFile(privKeyPath)
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

// --- REPRO-CHECK ---

func runReproCheck(args []string) {
	fmt.Println("=== Reproduction Check ===")
	log.Println("[WARN] repro-check not fully implemented in this single-file version without forcing timestamp.")
}

// --- HELPERS ---

func writeMeta(dir, timestamp string, timebox int, skipEval bool, evalMode string, 
	evalResultSha string, evalResultBytes int64,
	evalSrcRel string, evalSrcSha string, evalSrcBytes int64) {
	
	meta := fmt.Sprintf("timestamp=%s\n", timestamp)
	meta += fmt.Sprintf("timebox_sec=%d\n", timebox)
	meta += fmt.Sprintf("skip_eval=%v\n", skipEval)
	meta += fmt.Sprintf("eval_mode=%s\n", evalMode)
	meta += fmt.Sprintf("eval_result_sha256=%s\n", evalResultSha)
	meta += fmt.Sprintf("eval_result_bytes=%d\n", evalResultBytes)
	meta += fmt.Sprintf("eval_source_path=%s\n", evalSrcRel)
	meta += fmt.Sprintf("eval_source_sha256=%s\n", evalSrcSha)
	meta += fmt.Sprintf("eval_source_bytes=%d\n", evalSrcBytes)

	if err := os.WriteFile(filepath.Join(dir, "00_meta.txt"), []byte(meta), 0644); err != nil {
		log.Fatalf("[FATAL] write meta: %v", err)
	}
}

func listTrackedFiles() []string {
	out, err := exec.Command("git", "ls-files").Output()
	if err != nil {
		log.Fatalf("[FATAL] git ls-files: %v", err)
	}
	var files []string
	scanner := bufio.NewScanner(bytes.NewReader(out))
	for scanner.Scan() {
		f := strings.TrimSpace(scanner.Text())
		if f == "" {
			continue
		}
		files = append(files, f)
	}
	sort.Strings(files)
	return files
}

func scanNull(dir string, data []byte) {
	if bytes.Contains(data, []byte{0}) {
		_ = os.WriteFile(filepath.Join(dir, "20_null_bytes.txt"), []byte("NUL bytes detected\n"), 0644)
	}
}

func scanSecrets(dir string) {
	// Replaced by strict contamination checks in generatePackFilelist
	// Keeping this signature/call for naive scan if enabled, otherwise no-op or just report
	// We'll keep it as a 'naive scan' report generator for now, but not the enforcer.
	outPath := filepath.Join(dir, "21_secrets_scan.txt")
	var buf bytes.Buffer
	buf.WriteString("secret scan: naive patterns\n")

	diff, _ := exec.Command("git", "diff", "--cached").Output()
	combined := diff

	scanNull(dir, combined)
	re := regexp.MustCompile(`sk-[A-Za-z0-9]{20,}`)
	matches := re.FindAll(combined, -1)
	if len(matches) > 0 {
		buf.WriteString(fmt.Sprintf("FOUND %d potential secrets\n", len(matches)))
	} else {
		buf.WriteString("OK: no obvious secrets\n")
	}
	if err := os.WriteFile(outPath, buf.Bytes(), 0644); err != nil {
		log.Fatalf("[FATAL] write secrets scan: %v", err)
	}
}

func runMake(dir, logName string, cmdArgs []string, timeoutSec int, failCode int) {
	logPath := filepath.Join(dir, logName)
	logFile, err := os.Create(logPath)
	if err != nil {
		log.Fatal(err)
	}
	defer logFile.Close()

	ctxCmd := exec.Command(cmdArgs[0], cmdArgs[1:]...)
	ctxCmd.Stdout = logFile
	ctxCmd.Stderr = logFile
	ctxCmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := ctxCmd.Start(); err != nil {
		log.Fatalf("Failed to start %v: %v", cmdArgs, err)
	}

	done := make(chan error, 1)
	go func() {
		done <- ctxCmd.Wait()
	}()

	select {
	case <-time.After(time.Duration(timeoutSec) * time.Second):
		pgid, _ := syscall.Getpgid(ctxCmd.Process.Pid)
		_ = syscall.Kill(-pgid, syscall.SIGTERM)
		time.Sleep(2 * time.Second)
		_ = syscall.Kill(-pgid, syscall.SIGKILL)

		fmt.Fprintf(logFile, "\n[TIMEOUT] exceeded %ds\n", timeoutSec)
		fmt.Printf("[FAIL] timeout %v. See %s\n", cmdArgs, logName)
		os.Exit(124)
	case err := <-done:
		if err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				fmt.Fprintf(logFile, "\n[FAIL] exit code %d\n", exitErr.ExitCode())
				fmt.Printf("[FAIL] %v failed. See %s\n", cmdArgs, logName)
				os.Exit(failCode)
			}
		}
	}
}

func copyFile(src, dst string) {
	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		log.Fatalf(msgFatalMkdir, filepath.Dir(dst), err)
	}

	in, err := os.Open(src)
	if err != nil {
		log.Fatalf("[FATAL] open %s: %v", src, err)
	}
	defer func() { _ = in.Close() }()

	out, err := os.Create(dst)
	if err != nil {
		log.Fatalf(msgFatalCreate, dst, err)
	}
	defer func() { _ = out.Close() }()

	if _, err := io.Copy(out, in); err != nil {
		log.Fatalf("[FATAL] copy %s -> %s: %v", src, dst, err)
	}
}

// findLatestEvalResult scans for the latest timestamped jsonl in eval/results (ignoring latest.jsonl).
func findLatestEvalResult(repoRoot string) (string, string, error) {
	resultsDir := filepath.Join(repoRoot, dirEvalResults)
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		return "", "", fmt.Errorf("read %s: %w", resultsDir, err)
	}

	var candidates []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		if name == "latest.jsonl" {
			continue
		}
		if strings.HasSuffix(name, ".jsonl") {
			candidates = append(candidates, name)
		}
	}

	if len(candidates) == 0 {
		return "", "", fmt.Errorf("no .jsonl files found in %s (excluding latest.jsonl)", resultsDir)
	}

	// Sort by name (timestamp assumption: YYYYMMDD-HHMMSS...)
	sort.Strings(candidates)
	latest := candidates[len(candidates)-1]

	absPath := filepath.Join(resultsDir, latest)
	relPath := filepath.Join("eval/results", latest)
	return absPath, relPath, nil
}

// validateJsonlLooksOk checks if file exists, size > 0, and starts with '{'.
func validateJsonlLooksOk(absPath string) error {
	fi, err := os.Stat(absPath)
	if err != nil {
		return err
	}
	if fi.Size() == 0 {
		return fmt.Errorf("file is empty")
	}

	f, err := os.Open(absPath)
	if err != nil {
		return err
	}
	defer func() { _ = f.Close() }()

	scanner := bufio.NewScanner(f)
	if scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if !strings.HasPrefix(line, "{") {
			return fmt.Errorf("first line does not start with '{'")
		}
	} else {
		if err := scanner.Err(); err != nil {
			return err
		}
		return fmt.Errorf("file has no content to scan")
	}
	return nil
}

// copyEvalAsLatest copies the source jsonl to snapshot/eval/results/latest.jsonl
// and returns its sha256 and bytes.
func copyEvalAsLatest(snapshotDir, srcAbs string) (string, int64, string, error) {
	dstRel := "eval/results/latest.jsonl"
	dstAbs := filepath.Join(snapshotDir, dstRel)

	if err := os.MkdirAll(filepath.Dir(dstAbs), 0755); err != nil {
		return "", 0, "", fmt.Errorf("mkdir %s: %w", filepath.Dir(dstAbs), err)
	}

	// Copy
	srcF, err := os.Open(srcAbs)
	if err != nil {
		return "", 0, "", fmt.Errorf("open src %s: %w", srcAbs, err)
	}
	defer func() { _ = srcF.Close() }()

	dstF, err := os.Create(dstAbs)
	if err != nil {
		return "", 0, "", fmt.Errorf("create dst %s: %w", dstAbs, err)
	}
	defer func() { _ = dstF.Close() }() // Proper close handling in loop if needed, but here simple

	// TeeReader to calc sha256 while copying? Or just copy then calc?
	// Let's copy then calc to match existing patterns (fileSha256) or do it here efficiently.
	// Since we need to return sha/bytes, let's do it here.
	hasher := sha256.New()
	multi := io.MultiWriter(dstF, hasher)

	copied, err := io.Copy(multi, srcF)
	if err != nil {
		return "", 0, "", fmt.Errorf("copy failed: %w", err)
	}

	return fmt.Sprintf("%x", hasher.Sum(nil)), copied, dstAbs, nil
}

func runSelfVerify(dir string) {
	// Write self verify log, and include in checksums (already ensured by createManifestAndChecksums walking)
	logPath := filepath.Join(dir, fileSelfVerify)
	var buf bytes.Buffer
	buf.WriteString("self-verify: placeholder log\n")
	if err := os.WriteFile(logPath, buf.Bytes(), 0644); err != nil {
		log.Fatalf("[FATAL] write self verify log: %v", err)
	}
}

// --- REFACTORED HELPERS ---

func setupPackDir(packName string) (string, func()) {
	// Use a temp dir for construction
	tmpDir, err := os.MkdirTemp("", "reviewpack-*")
	if err != nil {
		log.Fatalf(msgFatalMkdirTemp, err)
	}
	packDir := filepath.Join(tmpDir, packName)
	if err := os.MkdirAll(packDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdirAll, err)
	}
	return packDir, func() {
		os.RemoveAll(tmpDir)
	}
}

func runPreflightChecks(repoRoot, packDir, timestamp string, timebox int, skipEval bool, mode string) {
	log.Println(msgDebugPreflight)
	// Write pending meta (pass 0/empty for results as they are unknown yet)
	writeMeta(packDir, timestamp, timebox, skipEval, mode, "", 0, "", "", 0)
	
	runCmd(repoRoot, "git", "status", ">", filepath.Join(packDir, fileStatus))

	// Strict clean check
	log.Println("DEBUG: Checking git status --porcelain...")
	cmd := exec.Command("git", "status", "--porcelain")
	cmd.Dir = repoRoot
	porcelainOut, err := cmd.Output()
	if err != nil {
		log.Fatalf(msgFatalGitStatus, err)
	}
	if len(bytes.TrimSpace(porcelainOut)) > 0 {
		log.Printf("[FATAL] preflight: working tree is dirty:\n%s", string(porcelainOut))
		os.Exit(1)
	}
}

func collectGitInfo(repoRoot, packDir, nCommits string) {
	runCmd(repoRoot, "git", "log", "-n", nCommits, "--stat", ">", filepath.Join(packDir, fileGitLog))
	runCmd(repoRoot, "git", "diff", "HEAD~"+nCommits, "HEAD", ">", filepath.Join(packDir, fileGitDiff))
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

func writeReadme(dir string) {
	content := `# review_pack

このアーカイブは「配って終わり」ではなく、**第三者が pack 単体で迷わず検証できる**状態に固定するためのものです。

## 1) 改ざん検出（必須）
まずはチェックサム検証：

` + "```bash" + `
bash VERIFY.sh
` + "```" + `

## 2) 厳密検証（任意 / Goが必要）
チェックサムに加えて **余計なファイル混入も拒否** します：

` + "```bash" + `
go run ./src_snapshot/cmd/reviewpack/main.go verify .
` + "```" + `

## 3) Gate-1（任意）
pack 内には ` + "`src_snapshot/eval/results/latest.jsonl`" + ` が同梱されています。
` + "`--verify-only`" + ` なら、環境チェックや再実行をせずに**結果だけ**を検証できます。

` + "```bash" + `
cd src_snapshot
bash ops/gate1.sh --verify-only
` + "```" + `
`
	path := filepath.Join(dir, "README.md")
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		log.Fatalf(msgFatalWrite, path, err)
	}
}

func writeVerifyScript(dir string) {
	script := `#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
echo "=== VERIFY (legacy wrapper) ==="
if [ ! -f "review_pack_v1" ]; then
    echo "[FAIL] Missing review_pack_v1 identity file"
    exit 1
fi
if ! grep -q " MANIFEST.tsv$" CHECKSUMS.sha256; then
  echo "[FATAL] CHECKSUMS.sha256 does not include MANIFEST.tsv" >&2
  exit 3
fi
if command -v sha256sum >/dev/null; then
  sha256sum -c CHECKSUMS.sha256
else
  shasum -a 256 -c CHECKSUMS.sha256
fi
echo "[OK] Checksums passed."
echo "[INFO] For strict verification (and extra-file detection), run:"
echo "  go run ./src_snapshot/cmd/reviewpack/main.go verify ."
`
	path := filepath.Join(dir, "VERIFY.sh")
	if err := os.WriteFile(path, []byte(script), 0755); err != nil {
		log.Fatalf(msgFatalWrite, path, err)
	}
}

func createManifestAndChecksums(dir string) {
	manifestPath := filepath.Join(dir, fileManifest)
	manFile, err := os.Create(manifestPath)
	if err != nil {
		log.Fatalf(msgFatalCreate, manifestPath, err)
	}
	defer func() { _ = manFile.Close() }()
	fmt.Fprintln(manFile, "path\tsha256\tbytes\tmode\ttype")

	var files []string
	if err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() || filepath.Base(path) == "MANIFEST.tsv" || filepath.Base(path) == "CHECKSUMS.sha256" {
			return nil
		}
		rel, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		files = append(files, rel)
		return nil
	}); err != nil {
		log.Fatalf("[FATAL] WalkDir: %v", err)
	}
	sort.Strings(files)

	var checksumLines []string
	for _, rel := range files {
		abs := filepath.Join(dir, rel)
		st, err := os.Stat(abs)
		if err != nil {
			log.Fatalf("[FATAL] stat %s: %v", abs, err)
		}
		mode := st.Mode().Perm()
		kind := "file"
		if st.Mode()&os.ModeSymlink != 0 {
			kind = "symlink"
		}
		h, err := fileSha256(abs)
		if err != nil {
			log.Fatalf("[FATAL] sha256 %s: %v", abs, err)
		}
		fmt.Fprintf(manFile, "%s\t%s\t%d\t%#o\t%s\n", rel, h, st.Size(), mode, kind)
		checksumLines = append(checksumLines, fmt.Sprintf("%s %s", h, rel))
	}

	manHash, err := fileSha256(manifestPath)
	if err != nil {
		log.Fatalf(msgFatalSha256, fileManifest, err)
	}
	checksumLines = append(checksumLines, fmt.Sprintf("%s %s", manHash, fileManifest))
	sort.Strings(checksumLines)

	checkPath := filepath.Join(dir, fileChecksums)
	if err := os.WriteFile(checkPath, []byte(strings.Join(checksumLines, "\n")+"\n"), 0644); err != nil {
		log.Fatalf(msgFatalWrite, fileChecksums, err)
	}
}

func check01Status(path string) error {
	b, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("missing 01_status.txt: %w", err)
	}
	s := string(b)
	if regexp.MustCompile(`(?mi)\bfatal\b`).MatchString(s) {
		return fmt.Errorf("01_status.txt contains 'fatal' (see %s)", path)
	}
	return nil
}

func findDirContainingFile(base, filename string, maxDepth int) (string, error) {
	base = filepath.Clean(base)
	baseDepth := strings.Count(base, string(os.PathSeparator))
	var found string

	err := filepath.WalkDir(base, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		depth := strings.Count(path, string(os.PathSeparator)) - baseDepth
		if depth > maxDepth {
			if d.IsDir() {
				return fs.SkipDir
			}
			return nil
		}
		if !d.IsDir() && filepath.Base(path) == filename {
			found = filepath.Dir(path)
			return io.EOF
		}
		return nil
	})

	if err != nil && err != io.EOF {
		return "", err
	}
	if found == "" {
		return "", fmt.Errorf("%s not found under %s", filename, base)
	}
	return found, nil
}

func fileSha256(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer func() { _ = f.Close() }() // nosemgrep

	hash := sha256.New()
	if _, err := io.Copy(hash, f); err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", hash.Sum(nil)), nil
}

func extractTar(tarFile, dstDir string) {
	f, err := os.Open(tarFile)
	if err != nil {
		log.Fatalf("[FATAL] open tar %s: %v", tarFile, err)
	}
	defer f.Close()
	gz, err := gzip.NewReader(f)
	if err != nil {
		log.Fatalf("[FATAL] gzip reader %s: %v", tarFile, err)
	}
	defer gz.Close()
	tr := tar.NewReader(gz)

	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Fatalf("[FATAL] tar read: %v", err)
		}
		target := filepath.Join(dstDir, header.Name)
		switch header.Typeflag {
		case tar.TypeDir:
			if err := os.MkdirAll(target, 0755); err != nil {
				log.Fatalf(msgFatalMkdir, target, err)
			}
		case tar.TypeReg:
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				log.Fatalf(msgFatalMkdir, filepath.Dir(target), err)
			}
			outFile, err := os.Create(target)
			if err != nil {
				log.Fatalf(msgFatalCreate, target, err)
			}
			if _, err := io.Copy(outFile, tr); err != nil {
				outFile.Close()
				log.Fatalf(msgFatalWrite, target, err)
			}
			outFile.Close()
		}
	}
}

func runCmd(dir, name string, args ...string) {
	// Simple wrapper for executing commands and handling redirection syntax roughly
	// This was present in the original code implicitly? No, it was used in runPack.
	// But wait, the original code had runCmd?
	// I missed copying `runCmd` from the original file!
	// I must add it.

	// Re-implementing a simple runCmd that handles ">" redirection if present in args
	// Logic: look for ">" and filename
	var cmdArgs []string
	var outFile string

	for i, arg := range args {
		if arg == ">" {
			if i+1 < len(args) {
				outFile = args[i+1]
				cmdArgs = args[:i]
				break
			}
		}
	}
	if outFile == "" {
		cmdArgs = args
	}

	c := exec.Command(name, cmdArgs...)
	c.Dir = dir

	if outFile != "" {
		f, err := os.Create(outFile)
		if err != nil {
			log.Fatalf(msgFatalCreate, outFile, err)
		}
		defer f.Close()
		c.Stdout = f
		c.Stderr = os.Stderr // or f? usually stderr goes to screen
	} else {
		// Just run
		// c.Stdout = os.Stdout
		// c.Stderr = os.Stderr
	}

	if err := c.Run(); err != nil {
		log.Fatalf("[FATAL] %s %v failed: %v", name, cmdArgs, err)
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func recordEvalMeta(packDir, snapshotDir string) {
	// Calculate hash of the included result
	resultPath := filepath.Join(snapshotDir, fileLatestJsonl)

	// Default values if missing (e.g. strict mode failed but we are packing anyway? verify check should catch it)
	// But let's be safe
	sha := "missing"
	size := int64(0)

	if info, err := os.Stat(resultPath); err == nil {
		size = info.Size()
		if s, err := fileSha256(resultPath); err == nil {
			sha = s
		}
	}

	f, err := os.OpenFile(filepath.Join(packDir, "00_meta.txt"), os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		log.Printf("[WARN] Could not update 00_meta.txt: %v", err)
		return
	}
	defer f.Close()

	fmt.Fprintf(f, "eval_result_sha256=%s\n", sha)
	fmt.Fprintf(f, "eval_result_bytes=%d\n", size)
}

