# Evidence Pipeline Runbook

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
ls -la /tmp/debug_pack
cat /tmp/debug_pack/METADATA.json
```

## IF_FAIL: Staging Residue
If the tool crashes during `pack`, temporary files might remain in `.local/evidence_store/tmp/`.
**Recovery**:
- Safe to delete contents of `.local/evidence_store/tmp/`.
- `evidencepack` cleans this directory on startup (if implemented) or you can run `rm -rf .local/evidence_store/tmp/*`.

## IF_FAIL: Store Corruption
If `index/packs.tsv` is corrupted or missing:
- **Rebuild**: Future versions of `evidencepack` generally support `index-rebuild`. For v1, you can list files in `packs/` to verify existence.
- The authoritative source of truth is the `packs/` directory. The index is an optimization/log.

## GC Safety
- Always run `evidencepack gc` (dry-run) first to check what will be deleted.
- Only run with `--apply` when confident.
