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

# 2.5 Env Metadata (S7-C07)
echo "[S7-CI] capturing env metadata..."
{
    echo "=== Environment Metadata ==="
    date
    uname -a
    bash --version | head -n1
    tar --version 2>&1 | head -n1
    curl --version | head -n1
    echo "============================"
} > "$OUT_DIR/env_meta.txt"

# 3. Download (S7-C04B)
PACK_FILE="$OUT_DIR/evidence_pack.tar.gz"
LOG_DOWNLOAD="$OUT_DIR/verify_download.log"

echo "[S7-CI] Downloading pack..."
if ! curl -fL "$EVIDENCE_PACK_URL" -o "$PACK_FILE" > "$LOG_DOWNLOAD" 2>&1; then
    echo "[FAIL] IF-01: Download failed. See $LOG_DOWNLOAD"
    echo "Ref: docs/ops/IF_FAIL_S7.md#if-01-download-fail"
    cat "$LOG_DOWNLOAD"
    exit 1
fi
echo "[OK] Downloaded $(stat -f%z "$PACK_FILE") bytes to $PACK_FILE"

# 4. List Content (S7-C04C)
LOG_TAR_LIST="$OUT_DIR/tar_list.log"
echo "[S7-CI] Listing tar content..."
if ! tar -tf "$PACK_FILE" > "$LOG_TAR_LIST"; then
    echo "[FAIL] Failed to list tar content. Corrupt?"
    exit 1
fi

# Check for markers (IF-03)
if ! grep -qE "evidence_pack_v1|review_pack_v1" "$LOG_TAR_LIST"; then
    echo "[FAIL] IF-03: Unknown pack format. No identity marker found."
    echo "Ref: docs/ops/IF_FAIL_S7.md#if-03-kind-missing"
    echo "See $LOG_TAR_LIST for content."
    exit 1
fi
echo "[OK] Format identity detected."

# 5. Verify SHA (S7-C04D)
LOG_SHA="$OUT_DIR/verify_sha256.log"
if [ -n "${EVIDENCE_PACK_SHA256:-}" ]; then
    echo "[S7-CI] Verifying SHA256..."
    CURRENT_SHA=$(shasum -a 256 "$PACK_FILE" | cut -d' ' -f1)
    echo "Expected: $EVIDENCE_PACK_SHA256" > "$LOG_SHA"
    echo "Actual:   $CURRENT_SHA" >> "$LOG_SHA"
    
    if [ "$CURRENT_SHA" != "$EVIDENCE_PACK_SHA256" ]; then
        echo "[FAIL] IF-02: SHA mismatch. See $LOG_SHA"
        echo "Ref: docs/ops/IF_FAIL_S7.md#if-02-sha-mismatch"
        exit 1
    fi
    echo "[OK] SHA256 matched."
else
    echo "SKIP: EVIDENCE_PACK_SHA256 not set" > "$LOG_SHA"
    echo "[INFO] Skipping SHA verification (not set)"
fi

# 6. Dispatcher Verify (S7-C04E)
LOG_DISPATCH="$OUT_DIR/verify_dispatch.log"
echo "[S7-CI] Running ops/verify_pack.sh..."
# Note: verify_pack.sh extracts and detects kind, but does NOT run inner verify yet if we stop here?
# Actually verify_pack.sh runs the inner verify script immediately if found.
# So this step covers S7-C04E AND S7-C04F effectively if we use ops/verify_pack.sh.
# But for S7-02 we want to capture logs.

if ! bash ops/verify_pack.sh "$PACK_FILE" > "$LOG_DISPATCH" 2>&1; then
    echo "[FAIL] IF-04/05: Verification failed. See $LOG_DISPATCH"
    echo "Ref: docs/ops/IF_FAIL_S7.md"
    cat "$LOG_DISPATCH"
    exit 1
fi
echo "[OK] Dispatcher & Inner Verification passed."

# 7. Success Marker (S7-C04G)
RESULT_FILE="$OUT_DIR/RESULT.ok"
date > "$RESULT_FILE"
echo "Verified: $PACK_FILE" >> "$RESULT_FILE"
echo "[S7-CI] SUCCESS: Artifact verified."
exit 0
