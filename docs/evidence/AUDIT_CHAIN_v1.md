# Audit Chain v1 Specification

## Overview

The audit chain provides an append-only, tamper-evident log of all evidence
pipeline events. Each entry is linked to its predecessor via a hash chain,
enabling deterministic verification of log integrity.

## Core Properties

- **Path**: `.local/reviewpack_artifacts/AUDIT_CHAIN_v1.tsv`
- **Format**: Tab-Separated Values (TSV)
- **Hashing**: `sha256(tab_join(cols_1_to_9))` (UTF-8, no trailing newline)
- **Columns**:
  1. `v`: Version (currently "1")
  2. `ts_utc`: ISO8601-like timestamp
  3. `pack_name`: Filename of the evidence pack
  4. `pack_sha256`: SHA256 of the `.tar.gz`
  5. `manifest_sha256`: SHA256 of `MANIFEST.tsv` inside the pack
  6. `checksums_sha256`: SHA256 of `CHECKSUMS.sha256` inside the pack
  7. `git_head`: Git HEAD (first 12 chars)
  8. `tool_ver`: Version of `evidencepack`
  9. `prev_entry_sha256`: Value of previous line's col 10 (Genesis: 64 zeros)
  10. `entry_sha256`: The hash of columns 1-9

## Genesis Hash

The `prev_entry_sha256` for the very first entry is 64 zero characters:

```
0000000000000000000000000000000000000000000000000000000000000000
```

## CLI Usage

```bash
# Register health-check
evidencepack health

# Automatic in bundle verification
evidencepack verify path/to/bundle.tar.gz
# → if audit/ directory exists in bundle, chain is verified automatically
```

## Smoke Test (S10-00A)

```bash
# 1. Create a pack (automatically appends to local chain)
KIND="s10test"
go run ./cmd/evidencepack pack --kind "$KIND" README.md
LATEST="$(ls -1t .local/evidence_store/packs/"$KIND"/evidence_"$KIND"_*.tar.gz | head -n 1)"

# 2. Verify health of the local chain
go run ./cmd/evidencepack health

# 3. Verify the pack (checks bundle chain if present)
go run ./cmd/evidencepack verify "$LATEST"
```

## Bundle Integration

- `evidencepack bundle --audit-dir <dir>` embeds the audit log snapshot.
- `evidencepack verify` on a bundle checks the embedded audit chain.
- **Policy**: If audit log is present and corrupt → verification fails.
  If audit log is absent → verification passes.
