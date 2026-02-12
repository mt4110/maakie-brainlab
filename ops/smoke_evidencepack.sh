#!/bin/bash
# ops/smoke_evidencepack.sh
# Deterministic end-to-end smoke test for evidencepack.
# Validates: keygen (seed) -> pack (embedded signing) -> verify -> health

set -euo pipefail

# (A) Execution location stability (no git dependency)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

# (C) Deterministic sorting
export LC_ALL=C

# Setup isolated environment
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Copy policy into isolated repo so --repo "$TMP_DIR" finds it
if [[ ! -f "$ROOT/ops/reviewpack_policy.toml" ]]; then
    echo "Error: missing policy: $ROOT/ops/reviewpack_policy.toml"
    exit 2
fi
mkdir -p "$TMP_DIR/ops"
cp "$ROOT/ops/reviewpack_policy.toml" "$TMP_DIR/ops/reviewpack_policy.toml"

echo "--- [SMOKE] Setup: $TMP_DIR"
STORE_DIR="$TMP_DIR/store"
PAYLOAD_DIR="$TMP_DIR/payload"
mkdir -p "$PAYLOAD_DIR"

# (B) Fixed payload (no date)
printf "s13 smoke payload\n" > "$PAYLOAD_DIR/README.txt"

# (F) Build-based execution for offline reliability
BIN="$TMP_DIR/evidencepack"
echo "--- [SMOKE] 0. Build"
go build -o "$BIN" ./cmd/evidencepack

KIND="s13test"

# --- Deterministic Ed25519 keypair via --seed ---
echo "--- [SMOKE] 1. Keygen (seed-based, deterministic)"
KEY_ID="smoke-test-key"
KEY_DIR="$TMP_DIR/ops/keys/reviewpack"
mkdir -p "$KEY_DIR"
"$BIN" keygen --id "$KEY_ID" --seed "reviewpack-smoke-v1" --out-dir "$KEY_DIR"
PRIV_KEY="$KEY_DIR/${KEY_ID}.key"

# Verify key files exist
if [[ ! -f "$PRIV_KEY" ]]; then
    echo "Error: Private key not generated: $PRIV_KEY"
    exit 3
fi
if [[ ! -f "$KEY_DIR/${KEY_ID}.pub" ]]; then
    echo "Error: Public key not generated: $KEY_DIR/${KEY_ID}.pub"
    exit 3
fi
echo "Keys generated: $KEY_DIR"

echo "--- [SMOKE] 2. Pack (with embedded signing)"
"$BIN" pack --kind "$KIND" --store "$STORE_DIR" --repo "$TMP_DIR" --sign-key "$PRIV_KEY" "$PAYLOAD_DIR"

echo "--- [SMOKE] 3. Locate Tar"
# (D) Deterministic discovery (dictionary order, last entry)
LATEST="$(find "$STORE_DIR/packs/$KIND" -maxdepth 1 -type f -name "evidence_${KIND}_*.tar.gz" | sort | tail -n 1)"

if [[ -z "$LATEST" ]]; then
    echo "Error: Resulting tarball not found in $STORE_DIR/packs/$KIND"
    ls -la "$STORE_DIR" "$STORE_DIR/packs" "$STORE_DIR/packs/$KIND" 2>/dev/null || true
    exit 3
fi
echo "Found: $LATEST"

# Verify SIGNATURES/ is embedded in the tar
echo "--- [SMOKE] 3a. Check embedded SIGNATURES/"
if ! tar tzf "$LATEST" | grep -q "^SIGNATURES/"; then
    echo "Error: SIGNATURES/ directory not found in tarball"
    tar tzf "$LATEST"
    exit 4
fi
echo "SIGNATURES/ found in tarball"

echo "--- [SMOKE] 4. Verify"
# (E) Flag-first order
"$BIN" verify --repo "$TMP_DIR" "$LATEST"

# Check that PubKeySHA256 is in the output
echo "--- [SMOKE] 4a. Verify PubKeySHA256 in output"
VERIFY_OUTPUT="$("$BIN" verify --repo "$TMP_DIR" "$LATEST" 2>&1)"
if ! echo "$VERIFY_OUTPUT" | grep -q "PubKeySHA256"; then
    echo "Error: PubKeySHA256 not found in verify output"
    echo "$VERIFY_OUTPUT"
    exit 5
fi
echo "PubKeySHA256 confirmed in verify output"

echo "--- [SMOKE] 5. Health"
"$BIN" health --repo "$TMP_DIR"

echo "--- [SMOKE] Result: PASS"
