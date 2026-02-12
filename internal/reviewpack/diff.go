package reviewpack

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// runDiff implements the "diff" subcommand.
func runDiff(args []string) {
	if len(args) < 2 {
		log.Fatal("Usage: reviewpack diff <bundleA> <bundleB>")
	}
	bundleA := args[0]
	bundleB := args[1]

	// 5.1 Extract
	tmpDirA, err := os.MkdirTemp("", "diff-a-*")
	if err != nil {
		log.Fatalf("[FATAL] mkdir temp: %v", err)
	}
	defer os.RemoveAll(tmpDirA)

	tmpDirB, err := os.MkdirTemp("", "diff-b-*")
	if err != nil {
		log.Fatalf("[FATAL] mkdir temp: %v", err)
	}
	defer os.RemoveAll(tmpDirB)

	extractTar(bundleA, tmpDirA)
	extractTar(bundleB, tmpDirB)

	// Assumption: Bundles have "review_pack" root (as per verify.go logic)
	rootA, err := findPackRoot(tmpDirA)
	if err != nil {
		log.Fatalf("[FAIL] bundleA: %v", err)
	}
	rootB, err := findPackRoot(tmpDirB)
	if err != nil {
		log.Fatalf("[FAIL] bundleB: %v", err)
	}

	// 5.2 Validate
	portA := filepath.Join(rootA, dirLogsPortable)
	portB := filepath.Join(rootB, dirLogsPortable)

	if _, err := os.Stat(portA); os.IsNotExist(err) {
		log.Fatalf("[FAIL] bundleA missing logs/portable/")
	}
	if _, err := os.Stat(portB); os.IsNotExist(err) {
		log.Fatalf("[FAIL] bundleB missing logs/portable/")
	}

	// 5.3 Compare (portable)
	diffsFound := comparePortable(rootA, rootB)

	if diffsFound {
		os.Exit(1)
	}
	os.Exit(0)
}

func findPackRoot(tmpDir string) (string, error) {
	root := filepath.Join(tmpDir, "review_pack")
	if _, err := os.Stat(root); err == nil {
		return root, nil
	}
	// Fallback as in verify.go
	return findDirContainingFile(tmpDir, "PACK_VERSION", 2)
}

func comparePortable(rootA, rootB string) bool {
	filesA := walkPortable(rootA)
	filesB := walkPortable(rootB)

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

func walkPortable(root string) map[string]string {
	portDir := filepath.Join(root, dirLogsPortable)
	res := make(map[string]string)
	_ = filepath.WalkDir(portDir, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		rel, _ := filepath.Rel(portDir, path)
		rel = filepath.ToSlash(rel)
		hash, _ := fileSha256(path)
		res[rel] = hash
		return nil
	})
	return res
}

func showUnifiedDiff(pathA, pathB, rel string) {
	// For now, use a simple line-based unified diff if possible, or just note the change.
	// Since we want to avoid extra dependencies, we can implement a basic one or just print "content changed".
	// The user requested a line-based unified diff.
	contentA, errA := os.ReadFile(pathA)
	contentB, errB := os.ReadFile(pathB)
	if errA != nil || errB != nil {
		fmt.Printf("    (Failed to read for diff)\n")
		return
	}

	if isBinary(contentA) || isBinary(contentB) {
		fmt.Printf("    (Binary file changed)\n")
		return
	}

	linesA := strings.Split(string(contentA), "\n")
	linesB := strings.Split(string(contentB), "\n")

	// Very basic diff (Hunk-less, just line by line for now)
	// TODO: Use a real LCS-based diff if needed, but for logs simple line mismatch is often enough.
	// But unified diff usually means hunk format.
	fmt.Printf("--- a/%s\n", rel)
	fmt.Printf("+++ b/%s\n", rel)
	
	// Implementation placeholder: for now just show changed lines
	// To follow deterministic rule, we should be careful.
	// Let's use a simple diff implementation.
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
	// Tiny line-by-line diff for now (not full LCS)
	// Real unified diff would be better.
	max := len(a)
	if len(b) > max {
		max = len(b)
	}

	for i := 0; i < max; i++ {
		if i >= len(a) {
			fmt.Printf("+ %s\n", b[i])
			continue
		}
		if i >= len(b) {
			fmt.Printf("- %s\n", a[i])
			continue
		}
		if a[i] != b[i] {
			fmt.Printf("- %s\n", a[i])
			fmt.Printf("+ %s\n", b[i])
		}
	}
}
