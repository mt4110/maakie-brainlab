# Signing Contract v1 (Crypto Layer)

This document defines the **Crypto Layer v1** contract for signing and verifying Evidence Packs.
It ensures that artifacts are cryptographically bound to a specific key, and that verification is deterministic.

## 1. Signing Target (Canonical Input)

The signature is generated over a **canonical UTF-8 message**.
The format is **strictly fixed** (order, newlines, no trailing newline at EOF).

```text
reviewpack.sig.v1
artifact_sha256=<hex>
checksums_sha256=<hex>
```

- **Line 1**: Version identifier (`reviewpack.sig.v1`).
- **Line 2**: `artifact_sha256` is the SHA-256 digest of the `.tar.gz` file (hex).
- **Line 3**: `checksums_sha256` is the SHA-256 digest of `CHECKSUMS.sha256` inside the pack (hex).
    - If `CHECKSUMS.sha256` is missing, signing **MUST** fail (S7 implementation).

**Note**: Timestamp is **NOT** included in the signed message. This ensures deterministic signatures for the same artifact and key.

### Algorithm
- **Ed25519** (pure Go implementation).

## 2. Signature Sidecar (`*.sig.json`)

The signature is stored in a JSON file adjacent to the artifact.
**Format**: `JSON` (Strict structure).
**Naming**: `<artifact_name>.sig.json` (e.g., `evidence_demo_...tar.gz.sig.json`).

```json
{
  "contract": "reviewpack.sig.v1",
  "alg": "ed25519",
  "key_id": "<string>",
  "artifact_sha256": "<hex>",
  "checksums_sha256": "<hex>",
  "signature_b64": "<base64>"
}
```

- `contract`: Must be `"reviewpack.sig.v1"`.
- `alg`: Must be `"ed25519"`.
- `key_id`: Identifier of the public key used for verification.
- `artifact_sha256`: Must match the artifact's digest.
- `checksums_sha256`: Must match the checksums file's digest.
- `signature_b64`: Ed25519 signature of the **Canonical Input** (see above), encoded in Base64 (Standard).

## 3. Key Management

### Public Keys
- Stored in repo: `ops/keys/reviewpack/<key_id>.pub`.
- Format: **JSON**.

```json
{
  "key_id": "<string>",
  "alg": "ed25519",
  "pub_b64": "<base64_32bytes>",
  "created_at_utc": "YYYY-MM-DDTHH:MM:SSZ"
}
```

### Private Keys
- **NEVER** stored in repo or pack.
- **NEVER** logged.
- Supplied via:
    1.  **File**: `--key-file <path>` (Raw 32-byte seed or 64-byte private key).
    2.  **Env**: `REVIEWPACK_PRIVATE_KEY_B64` (Base64 encoded).

## 4. Verification Logic (RunAlways)

1.  **Determine Target**: Identify `.tar.gz`.
2.  **Check Sidecar**: If `.sig.json` exists -> **VERIFICATION IS MANDATORY**.
    - If no `.sig.json` -> verification skipped (unless policy requires it in S8).
3.  **Read Sidecar**: Parse JSON. Check `contract="reviewpack.sig.v1"`, `alg="ed25519"`.
4.  **Load Key**: Find public key matching `key_id` in `ops/keys/reviewpack/`.
    - If key missing -> FAIL.
5.  **Reconstruct Message**:
    - Build canonical message using `artifact_sha256` and `checksums_sha256` from the **JSON** (Claimed).
6.  **Verify Signature**: `Ed25519.Verify(pub, message, sig)`.
    - If fail -> FAIL.
7.  **Verify Integrity**:
    - Compute actual SHA-256 of `.tar.gz`. Must match `artifact_sha256`.
    - Compute actual SHA-256 of `CHECKSUMS.sha256` (extract or read). Must match `checksums_sha256`.
    - If mismatch -> FAIL.

## 5. Audit Log (S7)

- **File**: `.local/reviewpack_audit/audit.log.jsonl`.
- **Append-only**.
- **Hash Chain**: `entry_hash` links to `prev_hash`.

**Entries**:
- `sign` event.
- `verify` event.
