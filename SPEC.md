# Reviewpack Specification (v1)

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

## 4. Test Evidence Markers (Pack-Contained)
In pack-contained verification, Gate-1 (verify-only) and strict verification require `30_make_test.log` to include evidence markers:
- `go test ./...`
- `unittest discover`
