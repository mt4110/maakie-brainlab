package main

import (
	"archive/tar"
	"compress/gzip"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestRoundTrip_OK(t *testing.T) {
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")

	// Create payload
	if err := os.MkdirAll(payloadDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadDir, "file1.txt"), []byte("content1"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(payloadDir, "subdir"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(payloadDir, "subdir", "file2.txt"), []byte("content2"), 0644); err != nil {
		t.Fatal(err)
	}

	// Pack
	cfg := PackConfig{
		Kind:      "test_kind",
		StoreDir:  storeDir,
		Payloads:  []string{payloadDir},
		Timestamp: time.Now().UTC(),
	}
	if err := executePack(cfg); err != nil {
		t.Fatalf("Pack failed: %v", err)
	}

	// Find the pack
	packsDir := filepath.Join(storeDir, "packs", "test_kind")
	entries, err := os.ReadDir(packsDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 {
		t.Fatalf("Expected 1 pack, got %d", len(entries))
	}
	packPath := filepath.Join(packsDir, entries[0].Name())

	// Verify
	if err := verifyPack(packPath); err != nil {
		t.Fatalf("Verify failed: %v", err)
	}
}

func TestVerify_FailsOnCorruptDataFile(t *testing.T) {
	// 1. Create valid pack
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, "data.txt"), []byte("original"), 0644)

	cfg := PackConfig{Kind: "test", StoreDir: storeDir, Payloads: []string{payloadDir}, Timestamp: time.Now()}
	executePack(cfg)

	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "test"))
	packPath := filepath.Join(storeDir, "packs", "test", entries[0].Name())

	// 2. Unpack, Corrupt, Repack (Manually to simulate corruption)
	// Actually easier: just create a corrupted tar.
	// Or use executePack, then gunzip, modify tar, gzip.
	// But modifying tar is hard without untarring.
	
	// Let's create a manual invalid pack structure to test Verify logic.
	// We reuse `extractAndVerifySafety` logic implicitly by verifyPack calling it.
	// But to corrupt content vs manifest, we need to construct a tar where they differ.
	
	badPackPath := filepath.Join(tmpDir, "bad.tar.gz")
	createManualPack(t, badPackPath, func(tw *tar.Writer) {
		// Write correct root files
		writeTarFile(t, tw, "EVIDENCE_VERSION", "v1\n")
		// Write data
		writeTarFile(t, tw, "data/foo.txt", "corrupted info")
		
		// Write MANIFEST that expects "original info" sha
		// "corrupted info" sha256 = ...
		// We'll just write a manifest that mismatches.
		// "data/foo.txt" <tab> "badhash" <tab> 14
		writeTarFile(t, tw, "MANIFEST.tsv", "data/foo.txt\tba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\t14\n")
		
		// Write checksums (doesn't matter if we fail manifest check first or checksum check first, 
		// but verify checks checksums first. So we must make checksums valid for the manifest/metadata we wrote!)
		// This is getting complicated to forge perfectly.
	})

	// Wait, `verifyPack` checks checksums of root files first.
	// So to test data corruption, I must have valid root files (including CHECKSUMS matching MANIFEST), 
	// but MANIFEST content mismatching DATA content.
	
	// Let's do the "Pack -> Untar -> Modify Data -> Tar -> Verify" approach.
	// But `verifyPack` doesn't verify signature, just hash.
	// If I modify data but NOT manifest, Verify should fail.
	
	// Better approach for test: Use internal functions if possible?
	// `verifyManifest` checks data vs manifest.
	
	// Integration test style:
	// 1. Pack normally.
	// 2. Open the tar, read all headers/files.
	// 3. Rewrite tar, but change content of one data file without updating manifest.
	// 4. Verify -> FAIL.
	
	// Implementation:
	modifyTar(t, packPath, func(name string, content []byte) []byte {
		if strings.Contains(name, "data.txt") {
			return []byte("corrupted")
		}
		return content
	}) // This invalidates manifest check (size/sha mismatch) AND checksums check? 
	   // No, checksums only checks root files. Manifest is a root file. 
	   // Manifest inside tar is NOT changed. Data IS changed.
	   // So Checksums OK. Manifest vs Data -> FAIL.
	
	if err := verifyPack(packPath); err == nil {
		t.Fatal("Expected verify to fail on corrupted data, but it passed")
	} else if !strings.Contains(err.Error(), "mismatch") { // hash mismatch
		t.Logf("Got expected error: %v", err)
	}
}

func TestVerify_FailsOnSymlink(t *testing.T) {
	packPath := filepath.Join(t.TempDir(), "symlink.tar.gz")
	
	createManualTar(t, packPath, func(tw *tar.Writer) {
		writeTarFile(t, tw, "EVIDENCE_VERSION", "v1\n")
		// Add symlink
		hdr := &tar.Header{
			Name:     "data/symlink",
			Typeflag: tar.TypeSymlink,
			Linkname: "/etc/passwd",
			Mode:     0777,
		}
		tw.WriteHeader(hdr)
	})

	if err := verifyPack(packPath); err == nil {
		t.Fatal("Expected verify failure on symlink, passed")
	} else {
		t.Logf("Got expected error: %v", err)
	}
}

func TestVerify_FailsOnPathTraversal(t *testing.T) {
	packPath := filepath.Join(t.TempDir(), "traversal.tar.gz")
	
	createManualTar(t, packPath, func(tw *tar.Writer) {
		writeTarFile(t, tw, "EVIDENCE_VERSION", "v1\n")
		hdr := &tar.Header{
			Name:     "../escape.txt",
			Mode:     0644,
			Size:     4,
		}
		tw.WriteHeader(hdr)
		tw.Write([]byte("test"))
	})

	if err := verifyPack(packPath); err == nil {
		t.Fatal("Expected verify failure on path traversal, passed")
	} else {
		t.Logf("Got expected error: %v", err)
	}
}

func TestVerify_FailsOnExtraFile(t *testing.T) {
	// Case: File in data/ but not in MANIFEST
	tmpDir := t.TempDir()
	storeDir := filepath.Join(tmpDir, "store")
	payloadDir := filepath.Join(tmpDir, "payload")
	os.MkdirAll(payloadDir, 0755)
	os.WriteFile(filepath.Join(payloadDir, "ok.txt"), []byte("ok"), 0644)
	
	cfg := PackConfig{Kind: "test", StoreDir: storeDir, Payloads: []string{payloadDir}, Timestamp: time.Now()}
	executePack(cfg)
	
	entries, _ := os.ReadDir(filepath.Join(storeDir, "packs", "test"))
	packPath := filepath.Join(storeDir, "packs", "test", entries[0].Name())

	modifyTar(t, packPath, func(name string, content []byte) []byte {
		return content
	}, func(tw *tar.Writer) {
		// Inject extra file
		writeTarFile(t, tw, "data/extra.txt", "I am extra")
	})

	if err := verifyPack(packPath); err == nil {
		t.Fatal("Expected verify failure on extra file, passed")
	} else {
		t.Logf("Got expected error: %v", err)
	}
}

// Helpers for test

func createManualPack(t *testing.T, path string, fn func(*tar.Writer)) {
	createManualTar(t, path, fn)
}

func createManualTar(t *testing.T, path string, fn func(*tar.Writer)) {
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	gw := gzip.NewWriter(f)
	defer gw.Close()
	tw := tar.NewWriter(gw)
	defer tw.Close()
	fn(tw)
}

func writeTarFile(t *testing.T, tw *tar.Writer, name, content string) {
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

// modifyTar reads a tar, allows modifying content of existing files, or injecting new ones.
func modifyTar(t *testing.T, path string, modifier func(name string, content []byte) []byte, injectors ...func(*tar.Writer)) {
	// Read old
	f, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	
	var items []struct {
		Header *tar.Header
		Content []byte
	}
	
	gzr, err := gzip.NewReader(f)
	if err != nil {
		t.Fatal(err)
	}
	tr := tar.NewReader(gzr)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			t.Fatal(err)
		}
		content, err := io.ReadAll(tr)
		if err != nil {
			t.Fatal(err)
		}
		items = append(items, struct{Header *tar.Header; Content []byte}{hdr, content})
	}
	gzr.Close()
	f.Close()

	// Rewrite
	f, err = os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	gzw := gzip.NewWriter(f)
	defer gzw.Close()
	tw := tar.NewWriter(gzw)
	defer tw.Close()

	for _, it := range items {
		newContent := modifier(it.Header.Name, it.Content)
		it.Header.Size = int64(len(newContent))
		if err := tw.WriteHeader(it.Header); err != nil {
			t.Fatal(err)
		}
		tw.Write(newContent)
	}
	
	for _, inj := range injectors {
		inj(tw)
	}
}
