package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"os"
	"path/filepath"
	"testing"
)

func TestDiff(t *testing.T) {
	t.Log("S9 Proof: intentional change v3")
	fmt.Println("LOG CHANGE PROOF")
	// Setup two temporary bundles
	tmpDir, err := os.MkdirTemp("", "diff-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	bundleA := filepath.Join(tmpDir, "A.tar.gz")
	bundleB := filepath.Join(tmpDir, "B.tar.gz")

	createTestBundle(t, bundleA, map[string]string{
		"review_pack/logs/portable/test.log": "line1\nline2\n",
		"review_pack/PACK_VERSION":           "1\n",
	})

	createTestBundle(t, bundleB, map[string]string{
		"review_pack/logs/portable/test.log": "line1\nline2changed\n",
		"review_pack/PACK_VERSION":           "1\n",
	})

	// Run diff (we can't easily capture stdout without redirecting Os.Stdout, 
	// but we can check if it runs without crashing and if we can mock the comparison)
	// For real testing, we should export comparePortable or similar.
	
	rootA := filepath.Join(tmpDir, "rootA")
	rootB := filepath.Join(tmpDir, "rootB")
	os.MkdirAll(filepath.Join(rootA, "logs/portable"), 0755)
	os.MkdirAll(filepath.Join(rootB, "logs/portable"), 0755)
	
	os.WriteFile(filepath.Join(rootA, "logs/portable/test.log"), []byte("line1\nline2\n"), 0644)
	os.WriteFile(filepath.Join(rootB, "logs/portable/test.log"), []byte("line1\nline2changed\n"), 0644)

	diffs := comparePortable(rootA, rootB, "text")
	if !diffs {
		t.Errorf("Expected differences found, but got none")
	}
}

func TestCompareRaw(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "raw-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	rootA := filepath.Join(tmpDir, "rootA")
	rootB := filepath.Join(tmpDir, "rootB")
	os.MkdirAll(filepath.Join(rootA, dirLogsRaw), 0755)
	os.MkdirAll(filepath.Join(rootB, dirLogsRaw), 0755)

	os.WriteFile(filepath.Join(rootA, dirLogsRaw, "test.raw"), []byte("raw1\n"), 0644)
	os.WriteFile(filepath.Join(rootB, dirLogsRaw, "test.raw"), []byte("raw2\n"),## 0) Preflight (absolute must)
- [x] `cd "$(git rev-parse --show-toplevel)"`
- [x] if `git status --porcelain=v1` is not empty -> error "dirty tree" -> STOP
- [x] `make ci-test`
- [x] if fail -> error "baseline ci-test failed" -> STOP
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [x] if fail -> error "verify-only baseline failed" -> STOP

---

## 1) Gate Checks (PR前ゲート; 먼저여기서落とす)
### 1.1 docs hygiene
- [x] if `rg -n 'file://' docs walkthrough -S` hits -> error "file:// remains" -> STOP
- [x] if `rg -n '```{4}carousel|````carousel' docs walkthrough -S` hits -> error "carousel block remains" -> STOP
- [x] continue

### 1.2 CLI flags exist (help)
- [x] run: `go run cmd/reviewpack/main.go diff --help | rg -n -- '--kind|--format'`
- [x] if no match -> error "flags not wired" -> STOP (Matched -kind/-format)
- [x] continue

---

## 2) Implementation Tasks (no silent failure)
### 2.1 STOP rule: ban os.Exit/log.Fatal in diff logic
- [x] if `rg -n 'os\.Exit\(|log\.Fatal' internal/reviewpack/diff.go -S` hits:
  - [x] else if those are only in top-level main/app layer:
    - [x] continue
  - [x] else -> error "diff logic uses os.Exit/log.Fatal" -> STOP

### 2.2 Implement CLI contract
- [x] if command wiring already exists:
  - [x] ensure `diff --kind` and `diff --format` are parsed and passed down
  - [x] continue

- [x] Define `runDiff(args) (code int)` style:
  - [x] if your framework uses Run() returning int -> use it
  - [x] continue

### 2.3 Implement exit code contract strictly
- [x] if no diffs -> return 0
- [x] else if diffs found -> return 1
- [x] else on any error -> return 2

### 2.4 Implement portable diff (portable-first)
- [x] Validate `logs/portable/` exists in both bundles
- [x] for each file under `logs/portable/**` (sorted)
- [x] normalize portable content (Step 2.6)
- [x] diff engine: `diff -u` preferred
- [x] continue

### 2.5 Implement raw mode (nucleus compare)
- [x] if `--kind raw|both`:
  - [x] compare `logs/raw/**/*.sha256` (sorted)
  - [x] continue

### 2.6 Log normalization (portable only; raw untouched)
- [x] Apply deterministic normalization: durations, cache markers, temp path suffixes.
- [x] continue

---

## 3) Tests (false-negative防止 + determinism)
- [x] Add/confirm tests
- [x] Run: `make ci-test`
- [x] if fail -> error "tests failed" -> STOP

---

## 4) Proof: Bundle-to-Bundle Demonstration (reality check)
- [/] Ensure clean git
- [/] Generate bundle A
- [/] Introduce controlled change
- [/] Commit controlled change
- [/] Generate bundle B
- [ ] Run diff:
  - [ ] `go run cmd/reviewpack/main.go diff --kind portable --format text <A> <B>` -> expect exit 1
  - [ ] `go run cmd/reviewpack/main.go diff --kind raw --format text <A> <B>` -> expect exit 1
- [ ] Validate bundle reality
644)

	diffs := compareRaw(rootA, rootB, "text")
	if !diffs {
		t.Errorf("Expected raw differences found, but got none")
	}
}

func TestRunDiffExitCodes(t *testing.T) {
	// Mock bundles
	tmpDir, err := os.MkdirTemp("", "cli-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	bundleA := filepath.Join(tmpDir, "A.tar.gz")
	bundleB := filepath.Join(tmpDir, "B.tar.gz")
	bundleC := filepath.Join(tmpDir, "C.tar.gz")

	createTestBundle(t, bundleA, map[string]string{
		"review_pack/logs/portable/test.log": "line1\n",
		"review_pack/PACK_VERSION":           "1\n",
	})
	createTestBundle(t, bundleB, map[string]string{
		"review_pack/logs/portable/test.log": "line1\n",
		"review_pack/PACK_VERSION":           "1\n",
	})
	createTestBundle(t, bundleC, map[string]string{
		"review_pack/logs/portable/test.log": "line1changed\n",
		"review_pack/PACK_VERSION":           "1\n",
	})

	// Case 0: No diff
	if code := runDiff([]string{bundleA, bundleB}); code != 0 {
		t.Errorf("Expected exit code 0 for identical bundles, got %d", code)
	}

	// Case 1: Diff found
	if code := runDiff([]string{bundleA, bundleC}); code != 1 {
		t.Errorf("Expected exit code 1 for different bundles, got %d", code)
	}

	// Case 2: Error (missing file)
	if code := runDiff([]string{bundleA, "nonexistent.tar.gz"}); code != 2 {
		t.Errorf("Expected exit code 2 for missing bundle, got %d", code)
	}
}

func TestNormalization(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "norm-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	src := filepath.Join(tmpDir, "raw.log")
	dst := filepath.Join(tmpDir, "port.log")

	content := "test\t0.123s\nbuild (cached)\n"
	os.WriteFile(src, []byte(content), 0644)

	createPortableLog(src, dst)

	got, _ := os.ReadFile(dst)
	expected := "test <DURATION>\nbuild <CACHED>\n"
	if string(got) != expected {
		t.Errorf("Normalization failed.\nGot: %q\nExp: %q", string(got), expected)
	}
}

func createTestBundle(t *testing.T, path string, files map[string]string) {
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()

	gw := gzip.NewWriter(f)
	defer gw.Close()
	tw := tar.NewWriter(gw)
	defer tw.Close()

	for name, content := range files {
		hdr := &tar.Header{
			Name: name,
			Mode: 0644,
			Size: int64(len(content)),
		}
		if err := tw.WriteHeader(hdr); err != nil {
			t.Fatal(err)
		}
		if _, err := tw.Write([]byte(content)); err != nil {
			t.Fatal(err)
		}
	}
}

func TestIsBinary(t *testing.T) {
	if isBinary([]byte("hello world")) {
		t.Errorf("Text incorrectly identified as binary")
	}
	if !isBinary([]byte{0, 1, 2, 3}) {
		t.Errorf("Binary incorrectly identified as text")
	}
}

func TestGetSortedPaths(t *testing.T) {
	a := map[string]string{"z": "1", "a": "2"}
	b := map[string]string{"b": "3", "a": "4"}
	sorted := getSortedPaths(a, b)
	if len(sorted) != 3 || sorted[0] != "a" || sorted[1] != "b" || sorted[2] != "z" {
		t.Errorf("Paths not sorted correctly: %v", sorted)
	}
}
