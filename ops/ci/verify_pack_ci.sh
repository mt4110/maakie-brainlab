#!/bin/bash
set -u

# ops/ci/verify_pack_ci.sh
# Entry point for CI-based verification of the Evidence Pack.
# Designed for S7-02 GitHub Actions workflow.

# 1. Setup Environment
# Default: 'out' directory for artifacts
OUT_DIR="${OUT_DIR:-out}"
mkdir -p "$OUT_DIR"

# 2. Safety Check (Usage)
if [ -z "${EVIDENCE_PACK_URL:-}" ]; then
    echo "Usage: EVIDENCE_PACK_URL=<url> $0"
    echo "Optional: EVIDENCE_PACK_SHA256=<sha256> (for verification)"
    exit 1
fi

echo "[S7-CI] Verify Pack CI Started"
echo "URL: $EVIDENCE_PACK_URL"
echo "OUT: $OUT_DIR"

# 3. Download (S7-C04B)
PACK_FILE="$OUT_DIR/evidence_pack.tar.gz"
LOG_DOWNLOAD="$OUT_DIR/verify_download.log"

echo "[S7-CI] Downloading pack..."
if ! curl -fL "$EVIDENCE_PACK_URL" -o "$PACK_FILE" > "$LOG_DOWNLOAD" 2>&1; then
    echo "[FAIL] IF-01: Download failed. See $LOG_DOWNLOAD"
    cat "$LOG_DOWNLOAD"
    exit 1
fi
echo "[OK] Downloaded $(stat -f%z "$PACK_FILE") bytes to $PACK_FILE"
