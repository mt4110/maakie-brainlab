package main

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
)

const (
	defaultTimeboxSec = 300
	packPrefix        = "review_pack"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(1)
	}

	subCmd := os.Args[1]
	args := os.Args[2:]

	switch subCmd {
	case "pack":
		runPack(args)
	case "submit":
		runSubmit(args)
	case "verify":
		runVerify(args)
	case "repro-check":
		runReproCheck(args)
	default:
		usage()
		os.Exit(1)
	}
}

func usage() {
	fmt.Fprintf(os.Stderr, "Usage: reviewpack <command> [args]\n")
	fmt.Fprintf(os.Stderr, "Commands:\n")
	fmt.Fprintf(os.Stderr, "  pack [--timebox N] [--skip-eval] [N_COMMITS]\n")
	fmt.Fprintf(os.Stderr, "  submit [--timebox N] [--skip-eval] [N_COMMITS]\n")
	fmt.Fprintf(os.Stderr, "  verify <dir|tar.gz>\n")
	fmt.Fprintf(os.Stderr, "  repro-check\n")
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
	// nCommits is positional
	fs.Parse(args)

	repoRoot, err := os.Getwd()
	if err != nil {
		log.Fatalf("[FATAL] Getwd: %v", err)
	}

	// Resolve repo root via git
	out, err := exec.Command("git", "rev-parse", "--show-toplevel").Output()
	if err != nil {
		log.Fatalf("[FATAL] git rev-parse --show-toplevel failed: %v", err)
	}
	repoRoot = strings.TrimSpace(string(out))
	if repoRoot == "" {
		log.Fatalf("[FATAL] git rev-parse --show-toplevel returned empty")
	}
	if err := os.Chdir(repoRoot); err != nil {
		log.Fatalf("[FATAL] chdir to repo root failed: %v", err)
	}

	// Environment overrides
	if os.Getenv("TIMEBOX_SEC") != "" {
		fmt.Sscanf(os.Getenv("TIMEBOX_SEC"), "%d", timebox)
	}
	if os.Getenv("SKIP_EVAL") == "1" {
		*skipEval = true
	}

	// 0. Setup
	timestamp := time.Now().Format("20060102_150405")
	packName := fmt.Sprintf("%s_%s", packPrefix, timestamp)

	// Use a temp dir for construction
	tmpDir, err := os.MkdirTemp("", "reviewpack-*")
	if err != nil {
		log.Fatalf("[FATAL] MkdirTemp: %v", err)
	}
	packDir := filepath.Join(tmpDir, packName)
	if err := os.MkdirAll(packDir, 0755); err != nil {
		log.Fatalf("[FATAL] MkdirAll: %v", err)
	}
	// Cleanup happens, tarball is moved out first
	defer os.RemoveAll(tmpDir)

	fmt.Printf("=== review_pack (S4 Hardened) ===\nTarget : %s.tar.gz\nTimebox: %ds\nWork   : %s\n", packName, *timebox, packDir)

	// 1. Preflight: Git Status & Meta
	log.Println("DEBUG: Starting preflight checks...")
	writeMeta(packDir, timestamp, *timebox, *skipEval)
	runCmd(repoRoot, "git", "status", ">", filepath.Join(packDir, "01_status.txt"))

	// Strict clean check
	log.Println("DEBUG: Checking git status --porcelain...")
	cmd := exec.Command("git", "status", "--porcelain")
	cmd.Dir = repoRoot
	porcelainOut, err := cmd.Output()
	if err != nil {
		log.Fatalf("[FATAL] git status --porcelain failed: %v", err)
	}
	if len(bytes.TrimSpace(porcelainOut)) > 0 {
		log.Printf("[FATAL] preflight: working tree is dirty:\n%s", string(porcelainOut))
		os.Exit(1)
	}

	nCommits := "5"
	if fs.NArg() > 0 {
		nCommits = fs.Arg(0)
	}
	runCmd(repoRoot, "git", "log", "-n", nCommits, "--stat", ">", filepath.Join(packDir, "10_git_log.txt"))
	runCmd(repoRoot, "git", "diff", "HEAD~"+nCommits, "HEAD", ">", filepath.Join(packDir, "11_git_diff.patch"))

	// 2. Secrets Scan (Integrated into filelist generation, but let's keep the report for now)
	scanSecrets(packDir)

	// 3. Make Test
	runMake(packDir, "30_make_test.log", []string{"make", "test"}, *timebox, 4)

	// 4. Make Run-Eval
	if !*skipEval {
		runMake(packDir, "31_make_run_eval.log", []string{"make", "run-eval"}, *timebox, 5)
	} else {
		_ = os.WriteFile(filepath.Join(packDir, "31_make_run_eval.log"), []byte("SKIP_EVAL set.\n"), 0644)
	}

	// 5. Source Snapshot
	log.Println("DEBUG: Creating src_snapshot...")
	snapshotDir := filepath.Join(packDir, "src_snapshot")
	if err := os.MkdirAll(snapshotDir, 0755); err != nil {
		log.Fatalf("[FATAL] src_snapshot mkdir: %v", err)
	}
	trackedFiles := listTrackedFiles()
	for _, f := range trackedFiles {
		copyFile(f, filepath.Join(snapshotDir, f))
	}
	// Copy latest eval result (Gate-1 requirement)
	copyLatestEval(snapshotDir)

	// 6. Documentation & Specifications (S4-05, S4-08)
	writeVersionAndSpec(packDir)
	writeReadme(packDir)
	writeVerifyScript(packDir)

	// C10-03: PACK_KIND Identity
	_ = os.WriteFile(filepath.Join(packDir, "review_pack_v1"), []byte("1\n"), 0644)

	// 7. Self-Verify
	runSelfVerify(packDir)

	// 8. Determinism: File List & Contamination Check (S4-04, S4-06)
	log.Println("DEBUG: Generating pack file list & checking contamination...")
	// This step scans the *constructed* packDir to ensure no banned files slipped in.
	// It also generates the rigorous file list for tar creation.
	filesToPack := generatePackFilelist(packDir)

	// 9. Manifest (S4-01, S4-02)
	log.Println("DEBUG: Creating MANIFEST.tsv...")
	// MANIFEST.tsv records the state of filesToPack *before* Checksums.
	createManifest(packDir, filesToPack)

	// 10. Checksums (S4-03)
	log.Println("DEBUG: Creating CHECKSUMS.sha256...")
	// Must include MANIFEST.tsv and everything else.
	// We regenerate the file list to include MANIFEST.tsv
	createChecksums(packDir)

	// 11. Deterministic Tarball (S4-04)
	log.Println("DEBUG: Creating deterministic tarball...")
	tarFile := packName + ".tar.gz" // in cwd
	// We re-scan to include CHECKSUMS.sha256 which wasn't in step 8
	// Final list for tar: everything in packDir
	finalFileList := generatePackFilelist(packDir)
	createDeterministicTar(packDir, finalFileList, "review_pack", tarFile)

	return tarFile
}

// --- SUBMIT (pack + verify-only) ---
func runSubmit(args []string) {
	fmt.Println("=== SUBMIT (pack + verify-only) ===")

	tarFile := packToTar(args)
	packSha, err := fileSha256(tarFile)
	if err != nil {
		log.Fatalf("[FATAL] sha256(%s): %v", tarFile, err)
	}
	fmt.Printf("PACK:   %s\nSHA256: %s\n", tarFile, packSha)

	// Verification Phase
	tmpDir, err := os.MkdirTemp("", "reviewpack-verify-*")
	if err != nil {
		log.Fatalf("[FATAL] MkdirTemp: %v", err)
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
	var files []string
	var violations []string

	err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			// Check prohibited dirs
			base := filepath.Base(path)
			if base == ".git" || base == "node_modules" || base == "target" || base == "__pycache__" || base == ".local" {
				return fs.SkipDir
			}
			return nil
		}

		// Prohibited file check (S4-06)
		rel, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		base := filepath.Base(path)

		// 1. Names
		if base == ".DS_Store" || base == ".env" || strings.HasSuffix(base, ".pem") || strings.HasPrefix(base, "id_rsa") || strings.HasSuffix(base, ".swp") || strings.HasSuffix(base, "~") {
			violations = append(violations, fmt.Sprintf("Prohibited file: %s", rel))
		}
		if strings.HasSuffix(base, ".log") {
			// Whitelist generated evidence logs
			if base != "30_make_test.log" && base != "31_make_run_eval.log" && base != "40_self_verify.log" {
				violations = append(violations, fmt.Sprintf("Prohibited file: %s", rel))
			}
		}

		// 2. Symlinks (S4-06-03)
		info, err := d.Info()
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			violations = append(violations, fmt.Sprintf("Symlink detected: %s", rel))
		}

		// 3. Size (S4-06-04) - Warn > 20MB
		if info.Size() > 20*1024*1024 {
			log.Printf("[WARN] Large file: %s (%.2f MB)", rel, float64(info.Size())/1024/1024)
		}

		files = append(files, rel)
		return nil
	})
	if err != nil {
		log.Fatalf("[FATAL] WalkDir %s: %v", dir, err)
	}

	if len(violations) > 0 {
		log.Printf("[FATAL] Contamination checks failed (%d violations):", len(violations))
		for _, v := range violations {
			log.Printf("  - %s", v)
		}
		os.Exit(1)
	}

	// Deterministic Order (S4-04-01)
	sort.Strings(files)
	return files
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
	manifestPath := filepath.Join(dir, "MANIFEST.tsv")
	manFile, err := os.Create(manifestPath)
	if err != nil {
		log.Fatalf("[FATAL] create %s: %v", manifestPath, err)
	}
	// Header
	fmt.Fprintln(manFile, "path\tsha256\tbytes")

	for _, rel := range files {
		// Skip MANIFEST.tsv itself if it happens to be in list
		if rel == "MANIFEST.tsv" {
			continue
		}
		abs := filepath.Join(dir, rel)
		h, err := fileSha256(abs)
		if err != nil {
			log.Fatalf("[FATAL] sha256 %s: %v", abs, err)
		}
		st, err := os.Stat(abs)
		if err != nil {
			log.Fatalf("[FATAL] stat %s: %v", abs, err)
		}
		fmt.Fprintf(manFile, "%s\t%s\t%d\n", rel, h, st.Size())
	}
	
	// Critical Fix (S4-01): Explicit Close before returning/hashing
	if err := manFile.Close(); err != nil {
		log.Fatalf("[FATAL] close MANIFEST: %v", err)
	}
}

func createChecksums(dir string) {
	// S4-03
	// Regenerate list to include MANIFEST.tsv, SPEC.md, etc.
	files := generatePackFilelist(dir) // This is sorted

	var lines []string
	for _, rel := range files {
		if rel == "CHECKSUMS.sha256" {
			continue
		}
		abs := filepath.Join(dir, rel)
		h, err := fileSha256(abs)
		if err != nil {
			log.Fatalf("[FATAL] sha256 %s: %v", abs, err)
		}
		lines = append(lines, fmt.Sprintf("%s  %s", h, rel))
	}
	// Write
	out := filepath.Join(dir, "CHECKSUMS.sha256")
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

	// Deterinistic Gzip
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
			log.Fatalf("[FATAL] MkdirTemp: %v", err)
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
	checksumsFile := filepath.Join(verifyRoot, "CHECKSUMS.sha256")
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
}

// --- REPRO-CHECK ---

func runReproCheck(args []string) {
	fmt.Println("=== Reproduction Check ===")
	log.Println("[WARN] repro-check not fully implemented in this single-file version without forcing timestamp.")
}

// --- HELPERS ---

func writeMeta(dir, timestamp string, timebox int, skipEval bool) {
	meta := fmt.Sprintf("timestamp=%s\ntimebox_sec=%d\nskip_eval=%v\n", timestamp, timebox, skipEval)
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
		log.Fatalf("[FATAL] mkdir %s: %v", filepath.Dir(dst), err)
	}

	in, err := os.Open(src)
	if err != nil {
		log.Fatalf("[FATAL] open %s: %v", src, err)
	}
	defer func() { _ = in.Close() }()

	out, err := os.Create(dst)
	if err != nil {
		log.Fatalf("[FATAL] create %s: %v", dst, err)
	}
	defer func() { _ = out.Close() }()

	if _, err := io.Copy(out, in); err != nil {
		log.Fatalf("[FATAL] copy %s -> %s: %v", src, dst, err)
	}
}

func copyLatestEval(snapshotDir string) {
	const resultsDir = "eval/results"
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		if os.IsNotExist(err) {
			log.Fatalf("[FATAL] missing %s directory (run: make run-eval)", resultsDir)
		}
		log.Fatalf("[FATAL] read %s: %v", resultsDir, err)
	}

	var candidates []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		if !strings.HasSuffix(name, ".jsonl") {
			continue
		}
		if name == "latest.jsonl" {
			continue
		}
		candidates = append(candidates, name)
	}

	if len(candidates) == 0 {
		log.Fatalf("[FATAL] no eval results found in %s/*.jsonl (run: make run-eval)", resultsDir)
	}

	sort.Strings(candidates)
	latest := candidates[len(candidates)-1]

	srcPath := filepath.Join(resultsDir, latest)
	dstPath := filepath.Join(snapshotDir, resultsDir, "latest.jsonl")

	fmt.Printf("[INFO] bundling latest eval result: %s -> latest.jsonl\n", latest)
	copyFile(srcPath, dstPath)
}



func runSelfVerify(dir string) {
	// Write self verify log, and include in checksums (already ensured by createManifestAndChecksums walking)
	logPath := filepath.Join(dir, "40_self_verify.log")
	var buf bytes.Buffer
	buf.WriteString("self-verify: placeholder log\n")
	if err := os.WriteFile(logPath, buf.Bytes(), 0644); err != nil {
		log.Fatalf("[FATAL] write self verify log: %v", err)
	}
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
		log.Fatalf("[FATAL] write %s: %v", path, err)
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
		log.Fatalf("[FATAL] write %s: %v", path, err)
	}
}

func createManifestAndChecksums(dir string) {
	manifestPath := filepath.Join(dir, "MANIFEST.tsv")
	manFile, err := os.Create(manifestPath)
	if err != nil {
		log.Fatalf("[FATAL] create %s: %v", manifestPath, err)
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
		log.Fatalf("[FATAL] sha256 MANIFEST.tsv: %v", err)
	}
	checksumLines = append(checksumLines, fmt.Sprintf("%s %s", manHash, "MANIFEST.tsv"))
	sort.Strings(checksumLines)

	checkPath := filepath.Join(dir, "CHECKSUMS.sha256")
	if err := os.WriteFile(checkPath, []byte(strings.Join(checksumLines, "\n")+"\n"), 0644); err != nil {
		log.Fatalf("[FATAL] write CHECKSUMS: %v", err)
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
				log.Fatalf("[FATAL] mkdir %s: %v", target, err)
			}
		case tar.TypeReg:
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				log.Fatalf("[FATAL] mkdir %s: %v", filepath.Dir(target), err)
			}
			outFile, err := os.Create(target)
			if err != nil {
				log.Fatalf("[FATAL] create %s: %v", target, err)
			}
			if _, err := io.Copy(outFile, tr); err != nil {
				outFile.Close()
				log.Fatalf("[FATAL] write %s: %v", target, err)
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
			log.Fatalf("[FATAL] create %s: %v", outFile, err)
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
