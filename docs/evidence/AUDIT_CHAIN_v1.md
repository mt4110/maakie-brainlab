# Audit Chain v1 Specification

## Overview

The audit chain provides an append-only, tamper-evident log of all evidence
pipeline events. Each entry is linked to its predecessor via a hash chain,
enabling deterministic verification of log integrity.

## File Location

- Working log: `.local/reviewpack_audit/audit.log.jsonl`
- Bundle snapshot: `audit/audit.log.jsonl` (inside provenance bundles)

## Entry Format (JSONL)

Each line is a JSON object with these fields (canonical order):

| Field            | Type   | Required | Description                           |
|------------------|--------|----------|---------------------------------------|
| `event_type`     | string | yes      | Event identifier (e.g., `sign`, `pack`) |
| `result`         | string | yes      | Outcome (`ok`, `fail`)               |
| `artifact_path`  | string | no       | Path to the artifact                  |
| `artifact_sha256`| string | no       | SHA-256 of the artifact               |
| `sig_path`       | string | no       | Path to signature sidecar             |
| `key_id`         | string | no       | Signing key identifier                |
| `git_sha`        | string | no       | Git commit SHA at event time          |
| `tool_version`   | string | no       | Tool version string                   |
| `utc_ts`         | string | yes      | ISO 8601 UTC timestamp                |
| `prev_hash`      | string | yes      | Hash of the previous entry            |
| `entry_hash`     | string | yes      | Hash of **this** entry                |

## Hash Computation

```
entry_hash = sha256(prev_hash + "\n" + canonical_json)
```

Where:

1. **`prev_hash`** is the `entry_hash` of the previous entry, or the genesis
   hash for the first entry.
2. **`canonical_json`** is `json.Marshal()` of the entry with `entry_hash`
   set to `""` (empty string). Field order follows Go struct tag order.

### Genesis Hash

The `prev_hash` for the very first entry is 64 zero characters:

```
0000000000000000000000000000000000000000000000000000000000000000
```

## Verification Algorithm

```
prevHash = GENESIS_HASH
for each line in audit_log.jsonl:
    entry = JSON.parse(line)
    assert entry.prev_hash == prevHash
    canonical = canonical_json(entry, entry_hash="")
    expected = sha256(prevHash + "\n" + canonical)
    assert entry.entry_hash == expected
    prevHash = entry.entry_hash
```

## CLI Usage

```bash
# Standalone verification
evidencepack audit verify path/to/audit.log.jsonl

# Automatic in bundle verification
evidencepack verify path/to/bundle.tar.gz
# → if audit/ directory exists in bundle, chain is verified automatically
```

## Bundle Integration

- `evidencepack bundle --audit-dir <dir>` embeds the audit log snapshot.
- `evidencepack verify` on a bundle checks the embedded audit chain.
- **Policy**: If audit log is present and corrupt → verification fails.
  If audit log is absent → verification passes (future: `--require-audit` flag).

## Breaking Changes from Pre-v1

- Genesis hash changed from `"GENESIS"` to 64-char zero hash.
- Entry hash now uses canonical JSON (deterministic field order).
- Existing logs written before v1 are incompatible and must be regenerated.
