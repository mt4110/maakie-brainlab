package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"crypto/sha256"
	"fmt"
	"io"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

func setupPackDir(packName string) (string, func()) {
	// Use a temp dir for construction
	tmpDir, err := os.MkdirTemp("", "reviewpack-*")
	if err != nil {
		log.Fatalf(msgFatalMkdirTemp, "reviewpack-*", err)
	}
	packDir := filepath.Join(tmpDir, packName)
	if err := os.MkdirAll(packDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdirAll, packDir, err)
	}
	return packDir, func() {
		os.RemoveAll(tmpDir)
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

func fileSha256(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer func() { _ = f.Close() }()

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
	if strings.HasSuffix(base, ".log") || strings.HasSuffix(base, ".log.sha256") || base == "rules-v1.json" {
		// Whitelist generated evidence logs and their structured counterparts
		if strings.HasPrefix(rel, "logs/") {
			return ""
		}
		// Legacy support for root logs
		if base == fileMakeTest || base == fileMakeEval || base == fileSelfVerify {
			return ""
		}
		return fmt.Sprintf("Prohibited file: %s", rel)
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
