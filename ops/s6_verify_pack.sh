#!/bin/bash
set -u

# S6 v1: Standalone Review Pack Verifier (Git-Free)
# Usage: bash ops/s6_verify_pack.sh <PACK_PATH>

PACK="${1:-}"

if [ -z "$PACK" ]; then
    echo "Usage: $0 <PACK_PATH>"
    exit 1
fi

if [ ! -f "$PACK" ]; then
    echo "[FAIL] Pack file not found: $PACK"
    exit 1
fi

echo "[S6] Verifying pack: $PACK"

# Setup temporary extraction
WORK_DIR=$(mktemp -d "/tmp/s6_verify.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

# Extract pack
if ! tar -xzf "$PACK" -C "$WORK_DIR"; then
    echo "[FAIL] Failed to extract pack."
    exit 1
fi

# 1. Check Required Paths
REQUIRED_PATHS=(
    "docs/rules"
    "ops/gate1.sh"
    "eval/results/latest.jsonl"
    "MANIFEST.txt"
)

MISSING=0
for p in "${REQUIRED_PATHS[@]}"; do
    if [ ! -e "$WORK_DIR/$p" ]; then
        echo "[FAIL] Missing required path: $p"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 1 ]; then
    echo "[FAIL] Pack structure invalid."
    exit 1
fi

# 2. Verify MANIFEST format=v1
MANIFEST="$WORK_DIR/MANIFEST.txt"
if ! grep -q "^format=v1$" "$MANIFEST"; then
    echo "[FAIL] MANIFEST.txt missing 'format=v1'."
    exit 1
fi

# 3. Verify Checksums
echo "[S6] Verifying file integrity (sha256)..."
# Extract checksums part
sed -n '/--- sha256 checksums ---/,$p' "$MANIFEST" | tail -n +2 > "$WORK_DIR/checksums.sha256"

if (cd "$WORK_DIR" && sha256sum -c checksums.sha256); then
    echo "[OK] Integrity check passed."
else
    echo "[FAIL] Integrity check failed."
    exit 1
fi

# 4. Optional Content Check (JSONL)
echo "[S6] Checking content (best effort)..."
LATEST_JSONL="$WORK_DIR/eval/results/latest.jsonl"
# Look for pass=true and sources=true (naive check)
if grep -q '"passed": true' "$LATEST_JSONL" && grep -q '"has_sources": true' "$LATEST_JSONL"; then
    echo "[OK] Found records with pass=true and has_sources=true."
# Since JSON boolean can be true with spaces, use robust grep or python?
# Requirement says "Warning-only check... best effort".
# grep is fine for now, user prompt said "pass=true & sources=true 相当を探索"
else
    echo "[WARN] Could not strictly verify 'passed': true AND 'has_sources': true in jsonl."
    echo "       This might be due to formatting or empty results."
fi

echo "=== S6 Verification Passed ==="
exit 0
