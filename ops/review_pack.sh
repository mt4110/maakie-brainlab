#!/usr/bin/env bash
set -euo pipefail

# macOS tar: avoid AppleDouble (._*) and extended attributes
export COPYFILE_DISABLE=1
export COPY_EXTENDED_ATTRIBUTES_DISABLE=1

# Usage: bash ops/review_pack.sh [N_COMMITS]
N_COMMITS="${1:-5}"
case "${N_COMMITS}" in
  ''|*[!0-9]*) N_COMMITS=5 ;;
esac
if [ "${N_COMMITS}" -lt 1 ]; then N_COMMITS=1; fi

# Safety: ensure we're inside a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "[FAIL] not inside a git repository" >&2
  exit 2
}

# Always work from repo root (prevents partial snapshot bugs)
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

MAX_COMMITS="$(git rev-list --count HEAD)"
if [ "${MAX_COMMITS}" -eq 0 ]; then
  echo "[FAIL] repository has no commits" >&2
  exit 2
fi
if [ "${N_COMMITS}" -gt "${MAX_COMMITS}" ]; then
  N_COMMITS="${MAX_COMMITS}"
fi

TIMEBOX_SEC="${TIMEBOX_SEC:-300}"   # default 5 minutes
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
PACK_NAME="review_pack_${TIMESTAMP}"
ARCHIVE="${PACK_NAME}.tar.gz"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/review_pack.${TIMESTAMP}.XXXXXX")"
PACK_DIR="${TMP_ROOT}/${PACK_NAME}"

# Keep debug dir on failure; delete on success
trap 'rc=$?; if [ $rc -eq 0 ]; then rm -rf "$TMP_ROOT"; else echo "[ERROR] review_pack failed (rc=$rc). Debug kept: $TMP_ROOT" >&2; fi' EXIT

echo "=== review_pack ==="
echo "Target : ${ARCHIVE}"
echo "Commits: last ${N_COMMITS}"
echo "Timebox: ${TIMEBOX_SEC}s"
echo "Work   : ${PACK_DIR}"

mkdir -p "${PACK_DIR}"

# 01: git status
git status > "${PACK_DIR}/01_status.txt"

# 10/11: log & patch
git log -n "${N_COMMITS}" --stat > "${PACK_DIR}/10_git_log.txt"
git format-patch -"${N_COMMITS}" --stdout > "${PACK_DIR}/11_git_diff.patch"

# 20: secrets scan (tracked files only)
# If secrets are found -> FAIL and DO NOT create archive.
if git grep -nE 'sk-[A-Za-z0-9]{20,}|BEGIN (RSA|EC|OPENSSH) PRIVATE KEY' > "${PACK_DIR}/20_secrets_scan.txt"; then
  echo "[FAIL] potential secrets found in tracked files. Aborting. See 20_secrets_scan.txt" >&2
  exit 3
else
  echo "No secrets found." > "${PACK_DIR}/20_secrets_scan.txt"
fi

# 30: make test (strict timeout, fail-fast)
set +e
python3 - <<'PY' > "${PACK_DIR}/30_make_test.log" 2>&1
import os, subprocess, sys
timeout = int(os.environ.get("TIMEBOX_SEC", "300"))
cmd = ["make", "test"]
print("[run]", " ".join(cmd))
try:
    r = subprocess.run(cmd, timeout=timeout)
    sys.exit(r.returncode)
except subprocess.TimeoutExpired:
    print(f"[TIMEOUT] make test exceeded {timeout}s", file=sys.stderr)
    sys.exit(124)
PY
TEST_RC=$?
set -e
if [ "${TEST_RC}" -ne 0 ]; then
  echo "[FAIL] make test failed (rc=${TEST_RC}). Aborting. See 30_make_test.log" >&2
  exit 4
fi

# 31: make run-eval (optional)
if [ -z "${SKIP_EVAL:-}" ]; then
  set +e
  python3 - <<'PY' > "${PACK_DIR}/31_make_run_eval.log" 2>&1
import os, subprocess, sys
timeout = int(os.environ.get("TIMEBOX_SEC", "300"))
cmd = ["make", "run-eval"]
print("[run]", " ".join(cmd))
try:
    r = subprocess.run(cmd, timeout=timeout)
    sys.exit(r.returncode)
except subprocess.TimeoutExpired:
    print(f"[TIMEOUT] make run-eval exceeded {timeout}s", file=sys.stderr)
    sys.exit(124)
PY
  EVAL_RC=$?
  set -e
  if [ "${EVAL_RC}" -ne 0 ]; then
    echo "[FAIL] make run-eval failed (rc=${EVAL_RC}). Aborting. See 31_make_run_eval.log" >&2
    exit 5
  fi
else
  echo "SKIP_EVAL set, skipping evaluation." > "${PACK_DIR}/31_make_run_eval.log"
fi

# src snapshot: ALL tracked files (robust; avoids allowlist regressions)
mkdir -p "${PACK_DIR}/src_snapshot"
git ls-files -z | while IFS= read -r -d '' f; do
mkdir -p "${PACK_DIR}/src_snapshot/$(dirname "$f")"
cp -p "$f" "${PACK_DIR}/src_snapshot/$f"
done

# Bundle latest eval result if exists
mkdir -p "${PACK_DIR}/src_snapshot/eval/results"
LATEST_RESULT_SRC="$(ls eval/results/*.jsonl 2>/dev/null | LC_ALL=C sort | tail -n1 || true)"
if [ -n "${LATEST_RESULT_SRC}" ]; then
    cp -p "${LATEST_RESULT_SRC}" "${PACK_DIR}/src_snapshot/eval/results/latest.jsonl"
else
    echo "[WARN] No eval/results/*.jsonl found." > "${PACK_DIR}/src_snapshot/eval/results/README_NO_RESULTS.txt"
fi

# README (simple)
cat > "${PACK_DIR}/README.md" <<'MD'
# review_pack
目的：第三者が pack 単体で検証できること。
まずやる：bash VERIFY.sh
MD

# VERIFY.sh
cat > "${PACK_DIR}/VERIFY.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== VERIFY ==="

echo "[1] sha256 check"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c CHECKSUMS.sha256
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c CHECKSUMS.sha256
else
    echo "[WARN] no sha256 tool found"
fi

echo "[2] Gate-1 (verify-only) if present"
if [ -f "src_snapshot/ops/gate1.sh" ]; then
    ( cd src_snapshot && bash ops/gate1.sh --verify-only )
else
    echo "[INFO] src_snapshot/ops/gate1.sh not found (skip)"
fi

echo "=== OK ==="
SH
chmod 755 "${PACK_DIR}/VERIFY.sh"

# MANIFEST + CHECKSUMS
: > "${PACK_DIR}/CHECKSUMS.sha256"
echo -e "path\tsha256\tbytes\tmode\ttype" > "${PACK_DIR}/MANIFEST.tsv"

(
    cd "${PACK_DIR}"
    find . -type f -not -name "CHECKSUMS.sha256" -print | LC_ALL=C sort | while IFS= read -r f; do
    clean="${f#./}"

    if command -v sha256sum >/dev/null 2>&1; then
        sha="$(sha256sum "$f" | awk '{print $1}')"
    else
        sha="$(shasum -a 256 "$f" | awk '{print $1}')"
    fi

    if [[ "${OSTYPE:-}" == darwin* ]]; then
        bytes="$(stat -f "%z" "$f")"
        mode="$(stat -f "%OLp" "$f")"
    else
        bytes="$(stat -c "%s" "$f")"
        mode="0$(stat -c "%a" "$f")"
    fi

    if [ "$clean" != "MANIFEST.tsv" ]; then
        echo -e "${clean}\t${sha}\t${bytes}\t${mode}\tfile" >> "MANIFEST.tsv"
    fi
    echo "${sha}  ${clean}" >> "CHECKSUMS.sha256"
    done
)

# Archive: create inside TMP_ROOT; move to cwd only on success
(
    cd "${TMP_ROOT}"
    if command -v gtar >/dev/null 2>&1; then
        gtar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -cf "${PACK_NAME}.tar" "${PACK_NAME}"
    else
        echo "[WARN] gtar not found. Archive determinism is best-effort on macOS." >&2
        tar --no-xattrs -cf "${PACK_NAME}.tar" "${PACK_NAME}" 2>/dev/null || tar -cf "${PACK_NAME}.tar" "${PACK_NAME}"
    fi
    gzip -n "${PACK_NAME}.tar"
)

mv "${TMP_ROOT}/${ARCHIVE}" "./${ARCHIVE}"
echo "[OK] created ${ARCHIVE}"
