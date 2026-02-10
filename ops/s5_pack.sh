#!/bin/bash
set -euo pipefail

# S5-02 Review Pack Generator
# Usage: bash ops/s5_pack.sh

# -----------------------------------------------------------------------------
# 1. Pre-flight Checks
# -----------------------------------------------------------------------------

# Check for clean git working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "[FAIL] Git working tree is dirty. Please commit or stash changes."
    exit 1
fi

# 0.1 Check for forbidden file[:]// links
bash ops/check_no_file_url.sh

# Check for required files
if [ ! -f "docs/rules" ] && [ ! -d "docs/rules" ]; then # docs/rules can be a dir or file depending on repo structure, prompt says "docs/rules exists"
    echo "[FAIL] docs/rules not found."
    exit 1
fi

if [ ! -f "ops/gate1.sh" ]; then
    echo "[FAIL] ops/gate1.sh not found."
    exit 1
fi

# -----------------------------------------------------------------------------
# 2. Setup & Execution
# -----------------------------------------------------------------------------

# Generate Timestamp (UTC)
TS=${TS:-$(date -u +"%Y%m%dT%H%M%SZ")}
PACK_DIR=".local/reviewpack_artifacts"
mkdir -p "$PACK_DIR"

GATE1_LOG="$PACK_DIR/gate1.$TS.log"

# S5_MODE Logic (Phase 04)
if [ "${S5_MODE:-}" == "verify-only" ]; then
    export GATE1_VERIFY_ONLY=1
    echo "[S5] Mode: verify-only (Skipping run-eval)"
fi

echo "[S5] Running Gate-1..."
if ! make gate1 > "$GATE1_LOG" 2>&1; then
    echo "[FAIL] Gate-1 failed. See log: $GATE1_LOG"
    exit 1
fi

# Extract Target result
# Look for "Target result: eval/results/..." in the log
MATCH_COUNT=$(grep -c "Target result:" "$GATE1_LOG" || true)

if [ "$MATCH_COUNT" -eq 0 ]; then
    echo "[FAIL] Could not extract Target result from Gate-1 log (0 matches)."
    echo "       Log: $GATE1_LOG"
    exit 1
elif [ "$MATCH_COUNT" -gt 1 ]; then
    echo "[FAIL] Multiple Target result lines found in Gate-1 log ($MATCH_COUNT matches)."
    echo "       Log: $GATE1_LOG"
    exit 1
fi

RESULT_SRC=$(grep "Target result:" "$GATE1_LOG" | awk '{print $3}')
echo "[S5] Target result: $RESULT_SRC"

# -----------------------------------------------------------------------------
# 3. Staging & Packing
# -----------------------------------------------------------------------------

# Setup staging with guaranteed cleanup
STAGE_DIR=$(mktemp -d "/tmp/s5_stage.XXXXXX")
trap 'rm -rf "$STAGE_DIR"' EXIT

echo "[S5] Staging dir: $STAGE_DIR"
mkdir -p "$STAGE_DIR/ops" "$STAGE_DIR/eval/results" "$STAGE_DIR/docs"

# Copy files
# Handle docs/rules being a file or directory
cp -r docs/rules "$STAGE_DIR/docs/"
cp ops/gate1.sh "$STAGE_DIR/ops/"
cp "$RESULT_SRC" "$STAGE_DIR/eval/results/latest.jsonl"

if [ -f "VERIFY" ]; then
    cp VERIFY "$STAGE_DIR/"
fi

# C10-04: Bundled Verifier
cp ops/VERIFY_EVIDENCE.sh "$STAGE_DIR/"
chmod +x "$STAGE_DIR/VERIFY_EVIDENCE.sh"



# C10-02: PACK_KIND Identity
echo "1" > "$STAGE_DIR/evidence_pack_v1"

# Generate MANIFEST.txt
MANIFEST="$STAGE_DIR/MANIFEST.txt"
HEAD_HASH=$(git rev-parse HEAD)

{
    echo "format=v1"
    echo "ts=$TS"
    echo "head=$HEAD_HASH"
    echo "result_src=$RESULT_SRC"
    echo "--- included files ---"
    (cd "$STAGE_DIR" && find . -type f ! -name "MANIFEST.txt" | sort | sed 's|^\./||')
    echo "--- sha256 checksums ---"
    (cd "$STAGE_DIR" && find . -type f ! -name "MANIFEST.txt" | sort | xargs sha256sum)
} > "$MANIFEST"

# Create tar.gz
PACK_NAME="evidence_pack_$TS.tar.gz"
PACK_PATH="$PACK_DIR/$PACK_NAME"

if [ -f "$PACK_PATH" ]; then
    # Collision: append random suffix (Method A)
    RAND=$(openssl rand -hex 4 2>/dev/null || date +%s)
    echo "[WARN] Pack file exists: $PACK_PATH. Appending suffix: $RAND"
    PACK_NAME="evidence_pack_${TS}_${RAND}.tar.gz"
    PACK_PATH="$PACK_DIR/$PACK_NAME"

    if [ -f "$PACK_PATH" ]; then
        echo "[FAIL] Pack file STILL exists after suffix (extremely unlikely): $PACK_PATH"
        echo "       Log: $GATE1_LOG"
        exit 1
    fi
fi

(cd "$STAGE_DIR" && COPYFILE_DISABLE=1 tar -czf - .) > "$PACK_PATH"

# Calculate pack SHA256
PACK_SHA=$(sha256sum "$PACK_PATH" | awk '{print $1}')

# S7-01: GPG Signing (Optional)
if [ -n "${S6_SIGNING_KEY:-}" ] && [ -f "${S6_SIGNING_KEY:-}" ]; then
    echo "[S5] Signing pack with key: $S6_SIGNING_KEY"
    go run cmd/gopsign/main.go -mode=sign -key="$S6_SIGNING_KEY" -target="$PACK_PATH"
    echo "[S5] Signature created: $PACK_PATH.asc"
fi

# Cleanup stage (handled by trap)
# rm -rf "$STAGE_DIR"

# -----------------------------------------------------------------------------
# 4. Finalize
# -----------------------------------------------------------------------------

# Update SUBMIT_HISTORY.sha256
HISTORY_FILE=".local/reviewpack_artifacts/SUBMIT_HISTORY.sha256"
# Format: <sha>  <packname>  head=<head>  ts=<TS>  result_src=<RESULT_SRC>
echo "$PACK_SHA  $PACK_NAME  head=$HEAD_HASH  ts=$TS  result_src=$RESULT_SRC" >> "$HISTORY_FILE"

HISTORY_ABS=$(cd "$(dirname "$HISTORY_FILE")" && pwd)/$(basename "$HISTORY_FILE")

echo ""
echo "=== S5 Review Pack Created ==="
echo "HEAD: $HEAD_HASH"
echo "PACK: $PACK_PATH"
echo "SHA:  $PACK_SHA"
echo "LOG:  $GATE1_LOG"
echo "HISTORY: $HISTORY_ABS"
echo "RESULT_SRC: $RESULT_SRC"

# Check for PRVerify log
PRVERIFY_DIR=".local/prverify"
PRVERIFY_LOG="n/a"

if [ -d "$PRVERIFY_DIR" ]; then
    # Find latest log
    LATEST_PRV=$(ls -t "$PRVERIFY_DIR"/prverify_* 2>/dev/null | head -n 1 || true)
    
    if [ -n "$LATEST_PRV" ]; then
        # Check content validation
        if grep -q "PR verify report" "$LATEST_PRV"; then
            PRVERIFY_LOG=$(cd "$(dirname "$LATEST_PRV")" && pwd)/$(basename "$LATEST_PRV")
        else
             # warnings to stderr, but don't fail
             echo "[WARN] PRVerify log found but content mismatch: $LATEST_PRV" >&2
        fi
    fi
fi

echo "PRVERIFY_LOG: $PRVERIFY_LOG"
# Check for optional PRVerify log (not implemented in this script but mentioned in reqs "if exists")
# Assuming it might be generated by something else or we just mention if we found one.
# For now, just listing what we have.

exit 0
