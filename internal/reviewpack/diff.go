package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

type DiffResult struct {
	Kind     string            `json:"kind"`
	Summary  DiffSummary       `json:"summary"`
	Added    []string          `json:"added"`
	Removed  []string          `json:"removed"`
	Modified []string          `json:"modified"`
}

type DiffSummary struct {
	Added    int `json:"added"`
	Removed  int `json:"removed"`
	Modified int `json:"modified"`
}

func (r DiffResult) Render(format string) {
	if format == "json" {
		b, _ := json.MarshalIndent(r, "", "  ")
		fmt.Println(string(b))
		return
	}

	fmt.Printf("Summary (%s): %d added, %d removed, %d modified\n", r.Kind, r.Summary.Added, r.Summary.Removed, r.Summary.Modified)
	for _, p := range r.Removed {
		fmt.Printf("[-] REMOVED (%s): %s\n", r.Kind, p)
	}
	for _, p := range r.Added {
		fmt.Printf("[+] ADDED (%s):   %s\n", r.Kind, p)
	}
	for _, p := range r.Modified {
		fmt.Printf("[!] MODIFIED (%s): %s\n", r.Kind, p)
	}
}

// runDiff implements the "diff" subcommand.
func runDiff(args []string) int {
	kind, format, cmdArgs, code := parseDiffFlags(args)
	if cmdArgs == nil {
		return code
	}

	bundleA, bundleB := cmdArgs[0], cmdArgs[1]
	tmpDirA, tmpDirB, code := prepareDiffDirs(bundleA, bundleB)
	if tmpDirA == "" {
		return code
	}
	defer os.RemoveAll(tmpDirA)
	defer os.RemoveAll(tmpDirB)

	rootA, rootB, code := resolvePackRoots(tmpDirA, tmpDirB)
	if rootA == "" {
		return code
	}

	diffsFound, err := executeComparisons(rootA, rootB, kind, format)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] %v\n", err)
		return 2
	}

	if diffsFound {
		return 1
	}
	return 0
}

func parseDiffFlags(args []string) (kind, format string, cmdArgs []string, exitCode int) {
	fs := flag.NewFlagSet("diff", flag.ContinueOnError)
	fs.SetOutput(os.Stdout)
	k := fs.String("kind", "portable", "Diff kind: portable, raw, both")
	f := fs.String("format", "text", "Output format: text, json")
	fs.Usage = func() {
		fmt.Fprintf(fs.Output(), "Usage: reviewpack diff <bundleA> <bundleB> [--kind portable|raw|both] [--format text|json]\n")
		fs.PrintDefaults()
	}

	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return "", "", nil, 0
		}
		return "", "", nil, 2
	}

	cmdArgs = fs.Args()
	if len(cmdArgs) < 2 {
		fs.Usage()
		return "", "", nil, 2
	}
	return *k, *f, cmdArgs, 0
}

func prepareDiffDirs(bundleA, bundleB string) (string, string, int) {
	tmpDirA, err := os.MkdirTemp("", "diff-a-*")
	if err != nil {
		return "", "", 2
	}
	tmpDirB, err := os.MkdirTemp("", "diff-b-*")
	if err != nil {
		os.RemoveAll(tmpDirA)
		return "", "", 2
	}

	if err := extractTarGraceful(bundleA, tmpDirA); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] bundleA: %v\n", err)
		return "", "", 2
	}
	if err := extractTarGraceful(bundleB, tmpDirB); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] bundleB: %v\n", err)
		return "", "", 2
	}
	return tmpDirA, tmpDirB, 0
}

func resolvePackRoots(tmpDirA, tmpDirB string) (string, string, int) {
	rootA, errA := findPackRoot(tmpDirA)
	rootB, errB := findPackRoot(tmpDirB)
	if errA != nil || errB != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] findPackRoot: A=%v, B=%v\n", errA, errB)
		return "", "", 2
	}
	return rootA, rootB, 0
}

func executeComparisons(rootA, rootB, kind, format string) (bool, error) {
	diffsFound := false
	if kind == "portable" || kind == "both" {
		found, err := comparePortable(rootA, rootB, format)
		if err != nil {
			return false, err
		}
		if found {
			diffsFound = true
		}
	}
	if kind == "raw" || kind == "both" {
		found, err := compareRaw(rootA, rootB, format)
		if err != nil {
			return false, err
		}
		if found {
			diffsFound = true
		}
	}
	return diffsFound, nil
}

func findPackRoot(tmpDir string) (string, error) {
	root := filepath.Join(tmpDir, "review_pack")
	if _, err := os.Stat(root); err == nil {
		return root, nil
	}
	// Fallback as in verify.go
	return findDirContainingFile(tmpDir, "PACK_VERSION", 2)
}

func comparePortable(rootA, rootB, format string) (bool, error) {
	filesA, errA := walkPortable(rootA)
	if errA != nil {
		return false, fmt.Errorf("walkA: %w", errA)
	}
	filesB, errB := walkPortable(rootB)
	if errB != nil {
		return false, fmt.Errorf("walkB: %w", errB)
	}

	sortedPaths := getSortedPaths(filesA, filesB)
	added, removed, modified := categorizeChanges(filesA, filesB, sortedPaths)
	diffFound := len(added) > 0 || len(removed) > 0 || len(modified) > 0

	res := DiffResult{
		Kind: "portable",
		Summary: DiffSummary{
			Added:    len(added),
			Removed:  len(removed),
			Modified: len(modified),
		},
		Added:    added,
		Removed:  removed,
		Modified: modified,
	}

	if format != "json" {
		fmt.Printf("Summary: %d added, %d removed, %d modified\n", len(added), len(removed), len(modified))
		for _, p := range removed {
			fmt.Printf("[-] REMOVED: %s\n", p)
		}
		for _, p := range added {
			fmt.Printf("[+] ADDED:   %s\n", p)
		}
		for _, p := range modified {
			fmt.Printf("[!] MODIFIED: %s\n", p)
			showUnifiedDiff(filepath.Join(rootA, dirLogsPortable, p), filepath.Join(rootB, dirLogsPortable, p), p)
		}
	} else {
		res.Render(format)
	}

	return diffFound, nil
}

func compareRaw(rootA, rootB, format string) (bool, error) {
	filesA, errA := walkRaw(rootA)
	if errA != nil {
		return false, fmt.Errorf("walkA(raw): %w", errA)
	}
	filesB, errB := walkRaw(rootB)
	if errB != nil {
		return false, fmt.Errorf("walkB(raw): %w", errB)
	}

	sortedPaths := getSortedPaths(filesA, filesB)
	added, removed, modified := categorizeChanges(filesA, filesB, sortedPaths)
	diffFound := len(added) > 0 || len(removed) > 0 || len(modified) > 0

	res := DiffResult{
		Kind: "raw",
		Summary: DiffSummary{
			Added:    len(added),
			Removed:  len(removed),
			Modified: len(modified),
		},
		Added:    added,
		Removed:  removed,
		Modified: modified,
	}
	if format != "json" {
		fmt.Println("--- RAW BUNDLE DIFF (Nucleus) ---")
	}
	res.Render(format)

	return diffFound, nil
}

func getSortedPaths(filesA, filesB map[string]string) []string {
	allPaths := make(map[string]bool)
	for p := range filesA {
		allPaths[p] = true
	}
	for p := range filesB {
		allPaths[p] = true
	}

	var sortedPaths []string
	for p := range allPaths {
		sortedPaths = append(sortedPaths, p)
	}
	sort.Strings(sortedPaths)
	return sortedPaths
}

func categorizeChanges(filesA, filesB map[string]string, sortedPaths []string) (added, removed, modified []string) {
	for _, p := range sortedPaths {
		hashA, inA := filesA[p]
		hashB, inB := filesB[p]

		if inA && !inB {
			removed = append(removed, p)
		} else if !inA && inB {
			added = append(added, p)
		} else if hashA != hashB {
			modified = append(modified, p)
		}
	}
	return
}

func walkPortable(root string) (map[string]string, error) {
	portDir := filepath.Join(root, dirLogsPortable)
	res := make(map[string]string)
	if _, err := os.Stat(portDir); os.IsNotExist(err) {
		return nil, fmt.Errorf("missing %s", dirLogsPortable)
	}
	err := filepath.WalkDir(portDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		rel, _ := filepath.Rel(portDir, path)
		rel = filepath.ToSlash(rel)
		hash, err := fileSha256(path)
		if err != nil {
			return err
		}
		res[rel] = hash
		return nil
	})
	return res, err
}

func walkRaw(root string) (map[string]string, error) {
	rawDir := filepath.Join(root, dirLogsRaw)
	res := make(map[string]string)
	if _, err := os.Stat(rawDir); os.IsNotExist(err) {
		return nil, fmt.Errorf("missing %s", dirLogsRaw)
	}

	// First, identify all files to check for sidecar compliance
	allFiles := make(map[string]bool)
	err := filepath.WalkDir(rawDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		rel, _ := filepath.Rel(rawDir, path)
		rel = filepath.ToSlash(rel)
		allFiles[rel] = true
		return nil
	})
	if err != nil {
		return nil, err
	}

	// Now implement nucleus contract:
	// 1. Every file must have a .sha256 sidecar (if it's not a .sha256 itself)
	// 2. We only compare the content of .sha256 files
	for rel := range allFiles {
		if strings.HasSuffix(rel, ".sha256") {
			content, err := os.ReadFile(filepath.Join(rawDir, rel))
			if err != nil {
				return nil, err
			}
			res[rel] = strings.TrimSpace(string(content))
			continue
		}
		// It's a data file (like .log). It MUST have a .sha256
		if !allFiles[rel+".sha256"] {
			return nil, fmt.Errorf("nucleus violation: %s is missing its .sha256 sidecar", rel)
		}
	}

	return res, nil
}

func extractTarGraceful(tarFile, dstDir string) error {
	f, err := os.Open(tarFile)
	if err != nil {
		return err
	}
	defer f.Close()
	gz, err := gzip.NewReader(f)
	if err != nil {
		return err
	}
	defer gz.Close()
	tr := tar.NewReader(gz)

	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		if err := extractEntry(dstDir, header, tr); err != nil {
			return err
		}
	}
	return nil
}

func extractEntry(dstDir string, header *tar.Header, tr *tar.Reader) error {
	target := filepath.Join(dstDir, header.Name)
	switch header.Typeflag {
	case tar.TypeDir:
		return os.MkdirAll(target, 0755)
	case tar.TypeReg:
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		outFile, err := os.Create(target)
		if err != nil {
			return err
		}
		defer outFile.Close()
		_, err = io.Copy(outFile, tr)
		return err
	}
	return nil
}

func showUnifiedDiff(pathA, pathB, rel string) {
	fmt.Printf("--- a/%s\n", rel)
	fmt.Printf("+++ b/%s\n", rel)

	contentA, errA := os.ReadFile(pathA)
	contentB, errB := os.ReadFile(pathB)
	if errA != nil || errB != nil {
		fmt.Printf("    (Failed to read for diff: A=%v, B=%v)\n", errA, errB)
		return
	}

	if isBinary(contentA) || isBinary(contentB) {
		fmt.Printf("    (Binary file changed)\n")
		return
	}

	if tryExternalDiff(pathA, pathB) {
		return
	}

	// Fallback
	linesA := strings.Split(string(contentA), "\n")
	linesB := strings.Split(string(contentB), "\n")
	diffLines(linesA, linesB)
}

func tryExternalDiff(pathA, pathB string) bool {
	cmd := exec.Command("diff", "-u", pathA, pathB)
	out, err := cmd.Output()
	if err == nil || (err != nil && cmd.ProcessState.ExitCode() == 1) {
		lines := strings.Split(string(out), "\n")
		maxLines := 100
		for i, line := range lines {
			if i >= maxLines {
				fmt.Printf("... (diff truncated after %d lines)\n", maxLines)
				break
			}
			if !strings.HasPrefix(line, "---") && !strings.HasPrefix(line, "+++") && line != "" {
				fmt.Println(line)
			}
		}
		return true
	}
	return false
}

func isBinary(data []byte) bool {
	for i := 0; i < min(len(data), 1024); i++ {
		if data[i] == 0 {
			return true
		}
	}
	return false
}

func diffLines(a, b []string) {
	maxLines := 50
	count := 0
	maxLen := len(a)
	if len(b) > maxLen {
		maxLen = len(b)
	}

	for i := 0; i < maxLen; i++ {
		if count >= maxLines {
			fmt.Printf("... (diff truncated after %d lines)\n", maxLines)
			break
		}
		if i >= len(a) {
			fmt.Printf("+ %s\n", b[i])
			count++
			continue
		}
		if i >= len(b) {
			fmt.Printf("- %s\n", a[i])
			count++
			continue
		}
		if a[i] != b[i] {
			fmt.Printf("- %s\n", a[i])
			fmt.Printf("+ %s\n", b[i])
			count += 2
		}
	}
}
// intentional change for diff
// intentional change v2
