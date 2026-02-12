package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"os"
	"path/filepath"
	"testing"
)

func TestDiff(t *testing.T) {
	t.Log("S9 Proof: intentional change")
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

	diffs := comparePortable(rootA, rootB)
	if !diffs {
		t.Errorf("Expected differences found, but got none")
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
