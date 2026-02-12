# Walkthrough: Trust Anchor v1 (Signer Identity Pinning)

Trust Anchor v1 enforces signer identity pinning via **PubKeySHA256 (SHA256 fingerprint)**,
not by human-readable KeyID labels.

## 1) Deterministic Keygen (`--seed`)

`keygen` supports `--seed` to deterministically generate the same keypair and fingerprint.
This keeps CI smoke stable without storing private keys in the repo.

```sh
$ evidencepack keygen --id smoke-test-key --seed "reviewpack-smoke-v1"
Generated keypair:
  Private: /tmp/.../smoke-test-key.key
  Public:  /tmp/.../smoke-test-key.pub
  PubKeySHA256: c70af1649edfc2fa4607922370f1fcce494c1bf1c14bb82e54f66fdf48dca00a
```

## 2) Fingerprint-Priority Policy Enforcement

Policy file: `ops/reviewpack_policy.toml`

In CI strict mode (`enforce_allowlist_in_ci=true`), enforcement priority is:

1.  **Priority 1: `allowed_pubkey_sha256` (cryptographic binding)**
2.  **Priority 2 fallback: `allowed_key_ids` (legacy label binding)**
3.  **Both empty: FAIL (misconfiguration)**

Example:

```toml
[keys]
allowed_key_ids = ["smoke-test-key"]
allowed_pubkey_sha256 = ["c70af1649edfc2fa4607922370f1fcce494c1bf1c14bb82e54f66fdf48dca00a"]
```

## 3) Enhanced Verification Logs

Verification logs always include:
- `KeyID`
- `PubKeySHA256`
- `PubKeySource`

Example:

```sh
$ evidencepack verify ...
VERIFIED: ...
  KeyID:        smoke-test-key
  PubKeySHA256: c70af1649edfc2fa4607922370f1fcce494c1bf1c14bb82e54f66fdf48dca00a
  PubKeySource: embedded
```

## 4) Proof of Work

Unit tests: `go test ./cmd/evidencepack/...`

Smoke test: `bash ops/smoke_evidencepack.sh`
