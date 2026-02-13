package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

// runDiff implements the "diff" subcommand.
func runDiff(args []string) int {
	fs := flag.NewFlagSet("diff", flag.ContinueOnError)
	kind := fs.String("kind", "portable", "Diff kind: portable, raw, both")
	format := fs.String("format", "text", "Output format: text, json")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}

	cmdArgs := fs.Args()
	if len(cmdArgs) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: reviewpack diff <bundleA> <bundleB> [--kind portable|raw|both] [--format text|json]\n")
		return 2
	}
	bundleA := cmdArgs[0]
	bundleB := cmdArgs[1]

	// 5.1 Extract
	tmpDirA, err := os.MkdirTemp("", "diff-a-*")
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] mkdir temp: %v\n", err)
		return 2
	}
	defer os.RemoveAll(tmpDirA)

	tmpDirB, err := os.MkdirTemp("", "diff-b-*")
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] mkdir temp: %v\n", err)
		return 2
	}
	defer os.RemoveAll(tmpDirB)

	if err := extractTarGraceful(bundleA, tmpDirA); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] bundleA: %v\n", err)
		return 2
	}
	if err := extractTarGraceful(bundleB, tmpDirB); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] bundleB: %v\n", err)
		return 2
	}

	rootA, err := findPackRoot(tmpDirA)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] findPackRoot bundleA: %v\n", err)
		return 2
	}
	rootB, err := findPackRoot(tmpDirB)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] findPackRoot bundleB: %v\n", err)
		return 2
	}

	diffsFound := false
	if *kind == "portable" || *kind == "both" {
		if comparePortable(rootA, rootB, *format) {
			diffsFound = true
		}
	}
	if *kind == "raw" || *kind == "both" {
		if compareRaw(rootA, rootB, *format) {
			diffsFound = true
		}
	}

	if diffsFound {
		return 1
	}
	return 0
}

func findPackRoot(tmpDir string) (string, error) {
	root := filepath.Join(tmpDir, "review_pack")
	if _, err := os.Stat(root); err == nil {
		return root, nil
	}
	// Fallback as in verify.go
	return findDirContainingFile(tmpDir, "PACK_VERSION", 2)
}

func comparePortable(rootA, rootB, format string) bool {
	if format == "json" {
		fmt.Println("[WARN] json format not fully implemented for portable diff")
	}
	filesA, errA := walkPortable(rootA)
	if errA != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] walkA: %v\n", errA)
		return false
	}
	filesB, errB := walkPortable(rootB)
	if errB != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] walkB: %v\n", errB)
		return false
	}

	sortedPaths := getSortedPaths(filesA, filesB)
	added, removed, modified := categorizeChanges(filesA, filesB, sortedPaths)

	// Emit Summary
	fmt.Printf("Summary: %d added, %d removed, %d modified\n", len(added), len(removed), len(modified))

	// Details
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

	return len(added) > 0 || len(removed) > 0 || len(modified) > 0
}

func compareRaw(rootA, rootB, format string) bool {
	if format == "json" {
		fmt.Println("[WARN] json format not fully implemented for raw diff")
	}
	fmt.Println("--- RAW BUNDLE DIFF (Nucleus) ---")
	filesA, errA := walkRaw(rootA)
	if errA != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] walkA(raw): %v\n", errA)
		return false
	}
	filesB, errB := walkRaw(rootB)
	if errB != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] walkB(raw): %v\n", errB)
		return false
	}

	sortedPaths := getSortedPaths(filesA, filesB)
	added, removed, modified := categorizeChanges(filesA, filesB, sortedPaths)

	fmt.Printf("Summary (Raw): %d added, %d removed, %d modified\n", len(added), len(removed), len(modified))

	for _, p := range removed {
		fmt.Printf("[-] REMOVED (Raw): %s\n", p)
	}
	for _, p := range added {
		fmt.Printf("[+] ADDED (Raw):   %s\n", p)
	}
	for _, p := range modified {
		fmt.Printf("[!] MODIFIED (Raw): %s\n", p)
	}

	return len(added) > 0 || len(removed) > 0 || len(modified) > 0
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
	err := filepath.WalkDir(rawDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		rel, _ := filepath.Rel(rawDir, path)
		rel = filepath.ToSlash(rel)
		// nucleus comparison: only care about .sha256 if they exist, or the files themselves
		hash, err := fileSha256(path)
		if err != nil {
			return err
		}
		res[rel] = hash
		return nil
	})
	return res, err
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
		target := filepath.Join(dstDir, header.Name)
		switch header.Typeflag {
		case tar.TypeDir:
			if err := os.MkdirAll(target, 0755); err != nil {
				return err
			}
		case tar.TypeReg:
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return err
			}
			outFile, err := os.Create(target)
			if err != nil {
				return err
			}
			if _, err := io.Copy(outFile, tr); err != nil {
				outFile.Close()
				return err
			}
			outFile.Close()
		}
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

	// Try external diff -u
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
			if strings.HasPrefix(line, "---") || strings.HasPrefix(line, "+++") {
				continue
			}
			if line != "" {
				fmt.Println(line)
			}
		}
		return
	}

	// Fallback
	linesA := strings.Split(string(contentA), "\n")
	linesB := strings.Split(string(contentB), "\n")
	diffLines(linesA, linesB)
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
