# Signing Contract v1 (Crypto Layer)

This document defines the **Crypto Layer v1** contract for signing and verifying Evidence Packs.
It ensures that artifacts are cryptographically bound to a specific key, and that verification is deterministic.

## 1. Signing Target (Canonical Input)

### External Sidecar (legacy)

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

### Embedded Signatures (v1 primary)

When `--sign-key <path>` is used, the pack tar includes a `SIGNATURES/` directory:

```text
SIGNATURES/
  pack.sha256          # text: "<sha256hex>  CHECKSUMS.sha256\n"
  pack.sha256.sig      # raw Ed25519 signature (64 bytes) over the hex digest string
  pack.pub             # JSON public key (CryptoKey format)
```

**Signing target**: The SHA-256 hex digest of `CHECKSUMS.sha256` (the file's content hash).
The signature is `Ed25519.Sign(priv, []byte("<sha256hex>"))`.

**Why CHECKSUMS.sha256?** This file already contains hashes of all root files
(`EVIDENCE_VERSION`, `METADATA.json`, `MANIFEST.tsv`), which in turn bind to all
payload data. Signing its hash transitively covers the entire pack content.

**Determinism**: Same CHECKSUMS.sha256 + same key = same signature (Ed25519 is deterministic).

### Algorithm

- **Ed25519** (pure Go implementation).

## 2. Signature Sidecar (`*.sig.json`) — Legacy

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

## 3. Embedded Signature Verification (v1)

1. **Extract** `SIGNATURES/pack.sha256`, `SIGNATURES/pack.sha256.sig`, `SIGNATURES/pack.pub` from the tar.
2. **Parse digest**: Read the hex digest from `pack.sha256` (format: `<hex>  CHECKSUMS.sha256\n`).
3. **Load public key**: Parse `pack.pub` as JSON (`CryptoKey` format).
4. **Verify signature**: `Ed25519.Verify(pub, []byte(hexDigest), sigBytes)`.
5. **Verify integrity**: Recompute SHA-256 of `CHECKSUMS.sha256` from the tar. Must match claimed digest.
6. **CI enforcement**: If `SIGNATURES/` is absent and `CI=true` → **FAIL** ("signature required in CI").

## 4. Key Management

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
    1.  **File**: `--sign-key <path>` or `--key-file <path>` (Raw 32-byte seed or 64-byte private key, or base64).
    2.  **Env**: `REVIEWPACK_PRIVATE_KEY_B64` (Base64 encoded).

## 5. Keygen

The `evidencepack keygen` subcommand generates an Ed25519 keypair:

```sh
# Random key
evidencepack keygen --id <key-id> --out-dir <dir>

# Deterministic key (same seed = same key = same fingerprint)
evidencepack keygen --id <key-id> --seed "reviewpack-smoke-v1" --out-dir <dir>
```

Output:
- `<dir>/<key-id>.key` — private key (base64, 600 permissions)
- `<dir>/<key-id>.pub` — public key (JSON CryptoKey format)
- `PubKeySHA256: <hex>` — fingerprint of the public key

When `--seed` is used, the key is derived deterministically:
`ed25519.NewKeyFromSeed(sha256("reviewpack:keygen:v1:" + seed))`.
This ensures CI can regenerate the same key without storing secrets.

## 6. Trust Anchor v1 — Signer Identity Pinning

### 6.1 PubKeySHA256 (fingerprint)

```
fingerprint = hex(sha256(pubkey_bytes))   # lowercase
```

- `pubkey_bytes` = raw 32-byte Ed25519 public key (no PEM wrapper)
- This is the **security binding** — KeyID is just a human label

### 6.2 Verify Output (always)

Every verified pack MUST log:

```
  KeyID:        <string>
  PubKeySHA256: <hex>
  PubKeySource: embedded | file:<path>
```

### 6.3 Policy Enforcement (`ops/reviewpack_policy.toml`)

```toml
[keys]
allowed_pubkey_sha256 = ["<hex>", ...]   # fingerprint allowlist
allowed_key_ids = ["<id>", ...]          # legacy label allowlist
```

**Priority** (CI strict + `enforce_allowlist_in_ci = true`):

1. `allowed_pubkey_sha256` non-empty → **fingerprint enforce** (priority)
2. `allowed_pubkey_sha256` empty → `allowed_key_ids` enforce (compat fallback)
3. Both empty → **FAIL** (misconfiguration)

### 6.4 Failure Recovery (1-scroll template)

```
ERROR: signer pubkey is not allowed (Trust Anchor v1)
  Expected PubKeySHA256: [<hex>, ...]
  Got PubKeySHA256:      <hex>
  Policy: ops/reviewpack_policy.toml (keys.allowed_pubkey_sha256)
  Regen (smoke): evidencepack keygen --id <id> --seed "reviewpack-smoke-v1"
  Note: KeyID is a label; allowlist is enforced by PubKeySHA256
```

## 7. Audit Log (S7) — TSV Chain

Every `verify` operation that changes the state (or as an audit record) MUST append to the local audit chain.

- **File**: `.local/reviewpack_artifacts/AUDIT_CHAIN_v1.tsv`.
- **Format**: TSV (Tab Separated Values).
- **Append-only**: New entries are always added to the end.
- **Hash Chain**: Each entry contains `entry_sha256` which is computed over columns 1-9, and `prev_entry_sha256` which links to the previous line's hash.

### 7.1 Column Schema (Fixed Order)

| Col | Name | Description |
|---|---|---|
| 1 | `version` | Contract version (e.g., `v1`) |
| 2 | `timestamp_utc` | ISO8601 UTC timestamp |
| 3 | `pack_name` | Name of the verified pack |
| 4 | `pack_sha256` | SHA-256 of the tarball |
| 5 | `manifest_sha256` | SHA-256 of `MANIFEST.tsv` |
| 6 | `checksums_sha256`| SHA-256 of `CHECKSUMS.sha256` |
| 7 | `git_head` | Current git commit hash |
| 8 | `tool_version` | Version of the `evidencepack` tool |
| 9 | `prev_entry_sha256`| `entry_sha256` of the previous line (or 64 zeros for genesis) |
| 10| `entry_sha256` | SHA-256 of columns 1-9 (tab-joined) |

## 8. Key Rotation v1

Trust Anchor v1 では、運用中の鍵ローテーションを安全に行うために以下のフィールドを使用します。

### 8.1 Rotation Fields (`ops/reviewpack_policy.toml`)
- `primary_pubkey_sha256`: 現在推奨されるメインの鍵（SignerIsPrimary 判定に使用）。
- `revoked_pubkey_sha256`: 明示的に失効させた鍵のリスト。`allowed` に残っていても拒否されます。

### 8.2 Rotation Procedure
1. **新鍵生成**: `keygen` を実行。秘密鍵は `tmp` 等の安全な場所にのみ置き、リポジトリに含めない。
2. **許可登録**: 新鍵の `PubKeySHA256` を `allowed_pubkey_sha256` に追加。
3. **主鍵切替**: `primary_pubkey_sha256` を新鍵の `PubKeySHA256` に更新。
4. **旧鍵失効**: 旧鍵の `PubKeySHA256` を `revoked_pubkey_sha256` に追加。

> [!IMPORTANT]
> `revoked_pubkey_sha256` は `allowed_pubkey_sha256` よりも優先されます。失効リストに含まれている鍵による署名は、いかなる場合も拒否されます。
