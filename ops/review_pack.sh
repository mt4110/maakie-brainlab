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
# Use git ls-files to avoid untracked garbage
# Extended to include docs (.md) and ops scripts (.sh) for Gate-1 review
git ls-files | grep -E '\.py$|\.toml$|Makefile|\.md$|\.sh$' | while read -r file; do
    mkdir -p "${PACK_DIR}/src_snapshot/$(dirname "$file")"
    cp "$file" "${PACK_DIR}/src_snapshot/$file"
done

# 6. Verification (before cleanup)
echo "=== Verification ==="
if grep -qE "FAILED|Traceback|ERROR" "${PACK_DIR}/30_make_test.log"; then
  echo "[WARN] make test looks FAILED (see 30_make_test.log)"
else
  echo "[OK] make test looks PASSED"
fi

# 5. Create Archive
tar -czf "${ARCHIVE}" "${PACK_DIR}"
echo "Pack created: ${ARCHIVE}"

# 6. Cleanup
rm -rf "${PACK_DIR}"
echo "Cleanup done: ${PACK_DIR}"
