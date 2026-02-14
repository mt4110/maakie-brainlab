package reviewpack

import (
	"archive/tar"
	"compress/gzip"
	"fmt"
	"io"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

func writeVersionAndSpec(dir string) {
	// S4-05: S16-01: Bump to V2
	versionPath := filepath.Join(dir, filePackVersion)
	if err := os.WriteFile(versionPath, []byte(packVersionV2), 0644); err != nil {
		log.Fatalf(msgFatalWrite, versionPath, err)
	}

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

	## 4. Test Evidence Markers (Structured Logs)
	In pack-contained verification, Gate-1 (verify-only) and strict verification require logs to include evidence markers.
	- logs/raw/<step>.log: Raw execution log (Audit truth).
	- logs/raw/<step>.log.sha256: Hash for raw log integrity.
	- logs/portable/<step>.log: Sanitized view for portability.
	- logs/portable/rules-v1.json: Sanitization rules definition.

	Evidence markers in logs include:
	~~~
	go test ./...
	unittest discover
	~~~
	`
	specPath := filepath.Join(dir, "SPEC.md")
	if err := os.WriteFile(specPath, []byte(strings.ReplaceAll(spec, "\t", "    ")), 0644); err != nil {
		log.Fatalf(msgFatalWrite, specPath, err)
	}
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
		log.Fatalf(msgFatalWrite, out, err)
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
				log.Fatalf("[FATAL] copy content %s to tar: %v", abs, err)
			}
			data.Close()
		}
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

func writeReadme(dir string) {
	content := `# review_pack

このアーカイブは「配って終わり」ではなく、**第三者が pack 単体で迷わず検証できる**状態に固定するためのものです。

## 1) 改ざん検出（必須）
まずはチェックサム検証：

` + codeBlockBash + `
bash VERIFY.sh
` + "```" + `

## 2) 厳密検証（任意 / Goが必要）
チェックサムに加えて **余計なファイル混入も拒否** します：

` + codeBlockBash + `
go run ./src_snapshot/cmd/reviewpack/main.go verify .
` + "```" + `

## 3) Gate-1（任意）
pack 内には ` + "`src_snapshot/eval/results/latest.jsonl`" + ` が同梱されています。
` + "`--verify-only`" + ` なら、環境チェックや再実行をせずに**結果だけ**を検証できます。

` + codeBlockBash + `
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

func writeMeta(dir, timestamp string, timebox int, skipEval bool, evalMode string, skipTest bool,
	evalResultSha string, evalResultBytes int64,
	evalSrcRel string, evalSrcSha string, evalSrcBytes int64) {

	meta := fmt.Sprintf("timestamp=%s\n", timestamp)
	meta += fmt.Sprintf("timebox_sec=%d\n", timebox)
	meta += fmt.Sprintf("skip_eval=%v\n", skipEval)
	meta += fmt.Sprintf("skip_test=%v\n", skipTest)
	meta += fmt.Sprintf("eval_mode=%s\n", evalMode)
	meta += fmt.Sprintf("eval_result_sha256=%s\n", evalResultSha)
	meta += fmt.Sprintf("eval_result_bytes=%d\n", evalResultBytes)
	meta += fmt.Sprintf("eval_source_path=%s\n", evalSrcRel)
	meta += fmt.Sprintf("eval_source_sha256=%s\n", evalSrcSha)
	meta += fmt.Sprintf("eval_source_bytes=%d\n", evalSrcBytes)

	metaPath := filepath.Join(dir, "00_meta.txt")
	if err := os.WriteFile(metaPath, []byte(meta), 0644); err != nil {
		log.Fatalf(msgFatalWrite, metaPath, err)
	}
}
