package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDiff(t *testing.T) {
	t.Log("S9 Proof: intentional change v3")
	fmt.Println("LOG CHANGE PROOF FINAL MODIFIED")
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

	rootA := filepath.Join(tmpDir, "rootA")
	rootB := filepath.Join(tmpDir, "rootB")
	if err := os.MkdirAll(filepath.Join(rootA, "logs/portable"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(rootB, "logs/portable"), 0755); err != nil {
		t.Fatal(err)
	}
	
	os.WriteFile(filepath.Join(rootA, "logs/portable/test.log"), []byte("line1\nline2\n"), 0644)
	os.WriteFile(filepath.Join(rootB, "logs/portable/test.log"), []byte("line1\nline2changed\n"), 0644)

	diffs, err := comparePortable(rootA, rootB, "text")
	if err != nil {
		t.Fatal(err)
	}
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
	if err := os.MkdirAll(filepath.Join(rootA, dirLogsRaw), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(rootB, dirLogsRaw), 0755); err != nil {
		t.Fatal(err)
	}

	os.WriteFile(filepath.Join(rootA, dirLogsRaw, "test.raw"), []byte("raw1\n"), 0644)
	os.WriteFile(filepath.Join(rootA, dirLogsRaw, "test.raw.sha256"), []byte("hash1"), 0644)
	os.WriteFile(filepath.Join(rootB, dirLogsRaw, "test.raw"), []byte("raw2\n"), 0644)
	os.WriteFile(filepath.Join(rootB, dirLogsRaw, "test.raw.sha256"), []byte("hash2"), 0644)

	diffs, err := walkRaw(rootA)
	if err != nil { t.Fatal(err) }
	diffsB, err := walkRaw(rootB)
	if err != nil { t.Fatal(err) }

	if len(diffs) == 0 || len(diffsB) == 0 {
		t.Errorf("walkRaw returned empty map")
	}

	res, err := compareRaw(rootA, rootB, "text")
	if err != nil {
		t.Fatal(err)
	}
	if !res {
		t.Errorf("Expected raw differences found, but got none")
	}
}

func TestRawNucleusViolation(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "nucleus-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	rootA := filepath.Join(tmpDir, "rootA")
	rootB := filepath.Join(tmpDir, "rootB")
	if err := os.MkdirAll(filepath.Join(rootA, dirLogsRaw), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(rootB, dirLogsRaw), 0755); err != nil {
		t.Fatal(err)
	}

	// A has sidecar, B is missing it
	os.WriteFile(filepath.Join(rootA, dirLogsRaw, "test.log"), []byte("data"), 0644)
	os.WriteFile(filepath.Join(rootA, dirLogsRaw, "test.log.sha256"), []byte("hash"), 0644)
	os.WriteFile(filepath.Join(rootB, dirLogsRaw, "test.log"), []byte("data"), 0644)

	_, err = compareRaw(rootA, rootB, "text")
	if err == nil || !strings.Contains(err.Error(), "nucleus violation") {
		t.Errorf("Expected nucleus violation error for missing sidecar, got %v", err)
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

	content := "test\t0.123s\nbuild (cached)\n<TMPDIR>/tmp123abc/data\n"
	os.WriteFile(src, []byte(content), 0644)

	createPortableLog(src, dst)

	got, _ := os.ReadFile(dst)
	expected := "test <DURATION>\nbuild <CACHED>\n<TMPDIR>/<RAND>/data\n"
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
			t.Fatal(hdr.Name, err)
		}
		if _, err := tw.Write([]byte(content)); err != nil {
			t.Fatal(hdr.Name, err)
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
