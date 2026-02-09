#!/bin/bash
set -euo pipefail

# ops/VERIFY_EVIDENCE.sh
# Standalone verifier for Evidence Pack (v1)
# Designed to be bundled INSIDE the pack at root.

# 1. Location Check
DIR=$(cd "$(dirname "$0")" && pwd)
MANIFEST="$DIR/MANIFEST.txt"
PACK_KIND="$DIR/evidence_pack_v1"

echo "=== Evidence Pack Verification ==="
echo "Root: $DIR"

# 2. Identity Check
if [ ! -f "$PACK_KIND" ]; then
    echo "[FAIL] Not an Evidence Pack (missing evidence_pack_v1)"
    exit 1
fi

# 3. Manifest Check
if [ ! -f "$MANIFEST" ]; then
    echo "[FAIL] Missing MANIFEST.txt"
    exit 1
fi

if ! grep -q "^format=v1$" "$MANIFEST"; then
    echo "[FAIL] Invalid MANIFEST format (missing format=v1)"
    exit 1
fi

# 4. Checksums
echo "Verifying integrity..."
# Create temp file for checksums
CHECKSUMS=$(mktemp)
trap 'rm -f "$CHECKSUMS"' EXIT

# Extract checksums from MANIFEST
sed -n '/--- sha256 checksums ---/,$p' "$MANIFEST" | tail -n +2 > "$CHECKSUMS"

# Verify
# We use cd $DIR to ensure relative paths work
if (cd "$DIR" && sha256sum -c "$CHECKSUMS"); then
    echo "[OK] All files verified."
else
    echo "[FAIL] Integrity check failed."
    exit 1
fi

echo "=== VERIFIED ==="
exit 0
