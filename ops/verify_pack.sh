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

# S7-01: Signature Verification
if [ -f "${PACK}.asc" ]; then
    echo "[verify_pack] Signature found: ${PACK}.asc"
    VERIFIED=0
    
    # Try GPG
    if command -v gpg >/dev/null 2>&1; then
        echo "[verify_pack] Verifying with GPG..."
        if gpg --verify "${PACK}.asc" "$PACK"; then
            echo "[PASS] Signature Verified (GPG)"
            VERIFIED=1
        else
            echo "[WARN] GPG verification failed (missing key?)"
        fi
    fi
    
    # Try gopsign if verification pending
    if [ $VERIFIED -eq 0 ] && [ -f "cmd/gopsign/main.go" ] && [ -n "${S6_VERIFY_KEY:-}" ]; then
        echo "[verify_pack] Verifying with gopsign (Key: $S6_VERIFY_KEY)..."
        if go run cmd/gopsign/main.go -mode=verify -key="$S6_VERIFY_KEY" -target="$PACK"; then
             echo "[PASS] Signature Verified (gopsign)"
             VERIFIED=1
        fi
    fi
    
    if [ $VERIFIED -eq 0 ]; then
        echo "[WARN] Could not verify signature (install gpg or set S6_VERIFY_KEY)"
    fi
fi

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

# 2. Review Pack (Nested review_pack/ or review_bundle/)
REVIEW_ROOT=""
if [ -d "$WORK_DIR/review_bundle" ] && [ -f "$WORK_DIR/review_bundle/review_pack_v1" ]; then
     REVIEW_ROOT="$WORK_DIR/review_bundle"
elif [ -d "$WORK_DIR/review_pack" ] && [ -f "$WORK_DIR/review_pack/review_pack_v1" ]; then
     REVIEW_ROOT="$WORK_DIR/review_pack"
fi

if [ -n "$REVIEW_ROOT" ]; then
    echo "[verify_pack] Detected: Review Pack (v1) at $(basename "$REVIEW_ROOT")"
    VERIFY_SCRIPT="$REVIEW_ROOT/VERIFY.sh"
    if [ -f "$VERIFY_SCRIPT" ]; then
        (cd "$REVIEW_ROOT" && bash VERIFY.sh)
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
