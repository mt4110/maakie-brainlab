#!/bin/bash
set -u

# ops/verify_pack.sh
# Unified Dispatcher (C10-05)
# Auto-detects pack kind and runs the appropriate verifier.

PACK="${1:-}"

if [ -z "$PACK" ]; then
    echo "Usage: $0 <PACK_PATH>"
    exit 1
fi

if [ ! -f "$PACK" ]; then
    echo "[FAIL] Pack file not found: $PACK"
    exit 1
fi

echo "[verify_pack] Verifying: $PACK"

# Setup work dir
WORK_DIR=$(mktemp -d "/tmp/verify_pack.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

# Extract (top-level only first to detect kind? No, just full extract for simplicity)
if ! tar -xzf "$PACK" -C "$WORK_DIR"; then
    echo "[FAIL] Failed to extract pack."
    exit 1
fi

# Detection Logic
# 1. Evidence Pack (Flat root, evidence_pack_v1)
if [ -f "$WORK_DIR/evidence_pack_v1" ]; then
    echo "[verify_pack] Detected: Evidence Pack (v1)"
    if [ -f "$WORK_DIR/VERIFY_EVIDENCE.sh" ]; then
        (cd "$WORK_DIR" && bash VERIFY_EVIDENCE.sh)
        exit $?
    else
        echo "[FAIL] Missing VERIFY_EVIDENCE.sh in Evidence Pack."
        exit 1
    fi
fi

# 2. Review Pack (Nested review_pack/, review_pack_v1)
if [ -d "$WORK_DIR/review_pack" ] && [ -f "$WORK_DIR/review_pack/review_pack_v1" ]; then
    echo "[verify_pack] Detected: Review Pack (v1)"
    VERIFY_SCRIPT="$WORK_DIR/review_pack/VERIFY.sh"
    if [ -f "$VERIFY_SCRIPT" ]; then
        # VERIFY.sh might not be executable by default in some tars if permission lost?
        # But Go creates it with 0644 usually? No, let's check.
        # It's better to explicitly bash it.
        (cd "$WORK_DIR/review_pack" && bash VERIFY.sh)
        exit $?
    else
        echo "[FAIL] Missing VERIFY.sh in Review Pack."
        exit 1
    fi
fi

# 3. Unknown
echo "[FAIL] Unknown pack format (No matching *pack_v1 identity found)."
ls -F "$WORK_DIR"
exit 1
