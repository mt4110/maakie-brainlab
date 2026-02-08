#!/bin/bash
set -euo pipefail

# S5-02 Review Pack Verifier
# Usage: bash ops/s5_verify_pack.sh <PACK_PATH>

PACK="$1"

if [ -z "$PACK" ]; then
    echo "Usage: $0 <PACK_PATH>"
    exit 1
fi

if [ ! -f "$PACK" ]; then
    echo "[FAIL] Pack file not found: $PACK"
    exit 1
fi

echo "[VERIFY] Checking pack: $PACK"

# Temporary extraction
TMP_DIR=$(mktemp -d)
tar -xzf "$PACK" -C "$TMP_DIR"

MANIFEST="$TMP_DIR/MANIFEST.txt"
if [ ! -f "$MANIFEST" ]; then
    echo "[FAIL] MANIFEST.txt not found inside pack."
    rm -rf "$TMP_DIR"
    exit 1
fi

# Verify HEAD
PACK_HEAD=$(grep "^head=" "$MANIFEST" | cut -d= -f2)
REPO_HEAD=$(git rev-parse HEAD)

if [ "$PACK_HEAD" != "$REPO_HEAD" ]; then
    echo "[FAIL] Pack HEAD ($PACK_HEAD) does not match current repo HEAD ($REPO_HEAD)."
    echo "       Please checkout the commit associated with this pack."
    rm -rf "$TMP_DIR"
    exit 1
fi

echo "[OK] HEAD matches: $PACK_HEAD"

# Verify SHA256 of staged files
echo "[VERIFY] Checking staged file integrity..."
# Extract sha256 checksums section
sed -n '/--- sha256 checksums ---/,$p' "$MANIFEST" | tail -n +2 > "$TMP_DIR/checksums.sha256"

# Verify using sha256sum
if (cd "$TMP_DIR" && sha256sum -c checksums.sha256); then
    echo "[OK] All packaged files verified."
else
    echo "[FAIL] File integrity check failed."
    rm -rf "$TMP_DIR"
    exit 1
fi

rm -rf "$TMP_DIR"
echo "=== Pack Verification Passed ==="
exit 0
