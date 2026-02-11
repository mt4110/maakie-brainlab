# Evidence Pipeline Runbook

## SMOKE TEST: Create and Verify (S10-00A)

```bash
# 1. Pack with arbitrary --kind label
STORE=".local/evidence_store"
KIND="s10test"
go run ./cmd/evidencepack pack --kind "$KIND" --store "$STORE" ./README.md

# 2. Locate the generated pack (it is stored under <store>/packs/<kind>/)
# TIP: If you lose track, use 'go run ./cmd/evidencepack kinds' to list kinds.
LATEST="$(ls -1t "$STORE/packs/$KIND"/evidence_"$KIND"_*.tar.gz | head -n 1)"

# 3. Verify
go run ./cmd/evidencepack verify "$LATEST"

# 4. Check Audit Chain Health
go run ./cmd/evidencepack health
```

## IF_FAIL: Verify Failed

If `evidencepack verify` fails, it exits with non-zero status.

### 1. Identify the Failure

The tool outputs the reason to `stderr`. Common causes:
- **Checksum Mismatch**: `CHECKSUMS.sha256` does not match root files.
- **Manifest Mismatch**: `data/` content differs from `MANIFEST.tsv`.
- **Safety Violation**: Absolute path, `..`, or symlink detected.

### 2. Debugging

To inspect the pack content without verified extraction:
```bash
mkdir -p /tmp/debug_pack
tar -xzf path/to/evidence.tar.gz -C /tmp/debug_pack
# Inspect contents
```

## IF_FAIL: Audit Chain Verification (S10)

If audit chain verification fails:

| Scenario | Impact | Recovery |
|----------|--------|----------|
| `prev_entry_sha256 mismatch` | Evidence chain broken; tampering or rebase detected. | Compare with backup; check if `.local` was cleared. |
| `entry_sha256 mismatch`      | Log line was modified manually. | Restore from backup or truncate to last valid line. |
| `No audit chain found`       | Provenance cannot be established (WARN). | Normal for early-stage packs; established after first verify. |

**Command to diagnose:**
```bash
evidencepack health
```
