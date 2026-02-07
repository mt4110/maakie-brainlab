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

echo "--- 31_make_run_eval.log ---"
make run-eval > "${PACK_DIR}/31_make_run_eval.log" 2>&1 || true

# 4. Collect Source Code (Tracked files only)
echo "--- Source Code ---"
mkdir -p "${PACK_DIR}/src_snapshot"

# Normalized collection: Sort by name (LC_ALL=C), filter strictly
echo "[pack] Collecting source files..."
# Extended to include docs (.md) and ops scripts (.sh) for Gate-1 review
# explicitly sort for determinism
git ls-files -z | sort -z | xargs -0n1 | grep -E '\.py$|\.toml$|Makefile|\.md$|\.sh$' | LC_ALL=C sort | while read -r file; do
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

# 5. Generate Manifest & Checksums (Deterministic)
echo "[pack] Generating MANIFEST.tsv & CHECKSUMS.sha256..."

# Header for Manifest
echo -e "path\tsha256\tbytes\tmode\ttype" > "${PACK_DIR}/MANIFEST.tsv"

# Find all files in PACK_DIR, sort strictly
# Use find to list, then standard tools to get stats/hash
# Relative paths from PACK_DIR
(
    cd "${PACK_DIR}"
    find . -type f -not -name "MANIFEST.tsv" -not -name "CHECKSUMS.sha256" -print0 | LC_ALL=C sort -z | while IFS= read -r -d '' f; do
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
            # stat -f "%z %p"
            read bytes mode_hex <<< $(stat -f "%z %p" "$f")
            # mode_hex is like 100644, we want last 4 octal? Actually standard `stat -c %a` is octal.
            # mac stat %p gives octal e.g. 100644. We want 0644.
            mode="${mode_hex: -4}"
        else
            # GNU stat
            read bytes mode <<< $(stat -c "%s %a" "$f")
            mode="0$mode" # simplistic padding if needed, but usually 644/755
        fi
        
        echo -e "${clean_path}\t${sha}\t${bytes}\t${mode}\tfile" >> "MANIFEST.tsv"
        echo "${sha}  ${clean_path}" >> "CHECKSUMS.sha256"
    done
)

# 6. Add VERIFY.sh (Self-contained verification)
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

# 2. Gate-1 Execution
echo "[verify] Running Gate-1 (src_snapshot/ops/gate1.sh)..."
if [ -f "src_snapshot/ops/gate1.sh" ]; then
    cd src_snapshot
    # Ensure it's executable (if zip/transfer lost it)
    chmod +x ops/gate1.sh
    # Mocking 'make' if missing? Gate-1 calls 'make gate1'.
    # Actually gate1.sh calls 'make test' and 'make run-eval'.
    # We need to assume the reviewer has the env or we just try to run the script.
    # The requirement is "pack単体で Gate-1 が実行できるか".
    # gate1.sh relies on 'make'. If make is not in pack, it relies on system 'make'.
    # src_snapshot contains Makefile.
    
    # Run gate1
    bash ops/gate1.sh
else
    echo "[FAIL] ops/gate1.sh not found in snapshot."
    exit 1
fi

echo "=== VERIFIED: Integrity & Logic OK ==="
EOF
chmod 755 "${PACK_DIR}/VERIFY.sh"

# 7. Create Archive (Deterministic attributes)
echo "=== Archiving ==="
# Tar options for reproducibility if available (GNU tar mostly)
# macOS tar (bsdtar) distinct options.
# We will use basic flags but rely on the content being fixed.
# If GNU tar is available as 'gtar', use it for --mtime etc?
# For now, standard tar.

tar -czf "${ARCHIVE}" "${PACK_DIR}"

echo "Pack created: ${ARCHIVE}"

# 8. Cleanup
rm -rf "${PACK_DIR}"
echo "Cleanup done: ${PACK_DIR}"
