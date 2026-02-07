#!/bin/bash
set -euo pipefail

# avoid macOS AppleDouble (._*) in tar
export COPYFILE_DISABLE=1

# S4.3 Review Pack Generator (Reusable)
# Usage: bash ops/review_pack.sh [N_COMMITS]

# Default to last 5 commits if not specified
N_COMMITS=${1:-5}
# Default base ref to HEAD~$N_COMMITS
BASE_REF="HEAD~$N_COMMITS"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACK_NAME="review_pack_${TIMESTAMP}"
PACK_DIR="${PACK_NAME}"
ARCHIVE="${PACK_NAME}.tar.gz"

echo "=== S4.3 Review Pack Generator ==="
echo "Target: ${ARCHIVE}"
echo "Commits: Last ${N_COMMITS} (from ${BASE_REF})"

# 1. Create Pack Directory
mkdir -p "${PACK_DIR}"

# 2. Collect Git Status & Diff
echo "--- 01_status.txt ---"
git status > "${PACK_DIR}/01_status.txt"

echo "--- 20_secrets_scan.txt ---"
# Scan tracked files only, capturing output but allowing 'no match' exit code
if git grep -nE 'sk-[A-Za-z0-9]{20,}|BEGIN (RSA|EC|OPENSSH) PRIVATE KEY' -- $(git ls-files); then
    echo "[WARN] Potential secrets found!"
else
    echo "No secrets found."
fi > "${PACK_DIR}/20_secrets_scan.txt"

echo "--- 10_git_log.txt ---"
git log -n "${N_COMMITS}" --stat > "${PACK_DIR}/10_git_log.txt"

echo "--- 11_git_diff.patch ---"
git format-patch -${N_COMMITS} --stdout > "${PACK_DIR}/11_git_diff.patch"

# 3. Collect Test Results
echo "--- 30_make_test.log ---"
# Capture both stdout and stderr, allow failure but log it
make test > "${PACK_DIR}/30_make_test.log" 2>&1 || true

if [ -z "${SKIP_EVAL:-}" ]; then
    echo "--- 31_make_run_eval.log ---"
    make run-eval > "${PACK_DIR}/31_make_run_eval.log" 2>&1 || true
else
    echo "--- 31_make_run_eval.log (SKIPPED) ---"
    echo "SKIP_EVAL set, skipping evaluation." > "${PACK_DIR}/31_make_run_eval.log"
fi

# 4. Collect Source Code (Tracked files only)
echo "--- Source Code ---"
mkdir -p "${PACK_DIR}/src_snapshot"

# Normalized collection: Sort by name (LC_ALL=C), filter strictly
echo "[pack] Collecting source files..."
# Extended to include docs (.md) and ops scripts (.sh) for Gate-1 review
# explicitly sort for determinism. Note: sort -z not supported on macOS, using standard sort (newline assumption)
git ls-files | grep -E '\.py$|\.toml$|Makefile|\.md$|\.sh$' | LC_ALL=C sort | while IFS= read -r file; do
    # Create dir structure
    mkdir -p "${PACK_DIR}/src_snapshot/$(dirname "$file")"
    
    # Copy with mode preservation (cp -p)
    cp -p "$file" "${PACK_DIR}/src_snapshot/$file"
    
    # Enforce permissions for determinism
    if [[ "$file" == *.sh ]]; then
        chmod 755 "${PACK_DIR}/src_snapshot/$file"
    else
        chmod 644 "${PACK_DIR}/src_snapshot/$file"
    fi
done

# 5. Generate Manifest, Checksums & Verify Script (Deterministic)
echo "[pack] Preparing MANIFEST.tsv, CHECKSUMS.sha256 & VERIFY.sh..."

# 5a. Bundle Latest Eval Result
echo "[pack] Bundling latest eval result..."
mkdir -p "${PACK_DIR}/src_snapshot/eval/results"
LATEST_RESULT_SRC=$(ls eval/results/*.jsonl 2>/dev/null | LC_ALL=C sort | tail -n1 || true)
if [ -n "$LATEST_RESULT_SRC" ]; then
    cp -p "$LATEST_RESULT_SRC" "${PACK_DIR}/src_snapshot/eval/results/latest.jsonl"
    echo "[pack] Bundled $LATEST_RESULT_SRC as src_snapshot/eval/results/latest.jsonl"
else
    echo "[WARN] No evaluation result found to bundle."
fi

# 5b. Add VERIFY.sh (Self-contained verification)
# Moved before manifest generation so it is included in checksums
cat << 'EOF' > "${PACK_DIR}/VERIFY.sh"
#!/usr/bin/env bash
set -euo pipefail

echo "=== Gate-1 Review Pack Verification ==="

# 1. Checksums
echo "[verify] Checking integrity (sha256)..."
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c CHECKSUMS.sha256
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c CHECKSUMS.sha256
else
    echo "[WARN] No sha256 tool found, skipping integrity check."
fi

# 2. Gate-1 Execution Check
echo "[verify] Checking Gate-1 readiness (Verify-Only)..."
if [ -f "src_snapshot/ops/gate1.sh" ] && [ -x "src_snapshot/ops/gate1.sh" ]; then
    echo "[OK] ops/gate1.sh exists and is executable."

    cd src_snapshot
    
    # Attempt Verify-Only Gate-1 (should pass with bundled results)
    echo "[verify] Running Gate-1 --verify-only..."
    if bash ops/gate1.sh --verify-only; then
        echo "[verify] Gate-1 VERIFIED (Proof of truthfulness present)."
    else
        echo "[FAIL] Gate-1 --verify-only FAILED."
        exit 1
    fi
    cd ..
else
    echo "[FAIL] ops/gate1.sh not found or not executable."
    exit 1
fi

echo "=== VERIFIED: Integrity & Proof OK ==="
EOF
chmod 755 "${PACK_DIR}/VERIFY.sh"

# 5c. Generate Manifest & Checksums
# Header for Manifest
echo -e "path\tsha256\tbytes\tmode\ttype" > "${PACK_DIR}/MANIFEST.tsv"

# Find all files in PACK_DIR, sort strictly
# Relative paths from PACK_DIR
(
    cd "${PACK_DIR}"
    # Note: sort -z is not available on BSD/macOS. 
    # We assume filenames do not contain newlines (safe for this repo).
    find . -type f -not -name "MANIFEST.tsv" -not -name "CHECKSUMS.sha256" -print | LC_ALL=C sort | while IFS= read -r f; do
        # Clean path (./foo -> foo)
        clean_path="${f#./}"
        
        # Calculate SHA256 (portable)
        if command -v sha256sum >/dev/null; then
            sha=$(sha256sum "$f" | cut -d' ' -f1)
        else
            sha=$(shasum -a 256 "$f" | cut -d' ' -f1)
        fi
        
        # Stat (bytes, mode) - platform specific handling
        if [[ "$OSTYPE" == "darwin"* ]]; then
            read bytes mode_hex <<< $(stat -f "%z %p" "$f")
            mode="${mode_hex: -4}"
        else
            read bytes mode <<< $(stat -c "%s %a" "$f")
            mode="0$mode"
        fi
        
        echo -e "${clean_path}\t${sha}\t${bytes}\t${mode}\tfile" >> "MANIFEST.tsv"
        echo "${sha}  ${clean_path}" >> "CHECKSUMS.sha256"
    done
)

# 6. Create Archive (Deterministic attributes)
echo "=== Archiving ==="
# avoid macOS xattrs and AppleDouble files
export COPYFILE_DISABLE=1

TAR_OPTS=("-czf" "${ARCHIVE}")
if [[ "$OSTYPE" == "darwin"* ]]; then
    # BSD tar on macOS
    TAR_OPTS+=("--no-xattrs")
fi
TAR_OPTS+=("${PACK_DIR}")

tar "${TAR_OPTS[@]}"

echo "Pack created: ${ARCHIVE}"

# 7. Cleanup
rm -rf "${PACK_DIR}"
echo "Cleanup done: ${PACK_DIR}"
