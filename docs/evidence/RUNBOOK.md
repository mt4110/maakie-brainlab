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
- `evidencepack` cleans this directory on startup (if implemented) or you can run
  `rm -rf .local/evidence_store/tmp/*`.

## IF_FAIL: Store Corruption

If `index/packs.tsv` is corrupted or missing:
- **Rebuild**: Future versions of `evidencepack` generally support `index-rebuild`.
  For v1, you can list files in `packs/` to verify existence.
- The authoritative source of truth is the `packs/` directory. The index is an optimization/log.

## GC Safety

- Always run `evidencepack gc` (dry-run) first to check what will be deleted.
- Only run with `--apply` when confident.

## IF_FAIL: Policy Violation (S8)

If verification fails due to policy:

1. **Check the Mode**: Output shows `Mode: strict (Environment: ci)`.
2. **Missing Signature**: If policy requires it (`require_signature_in_ci`),
   you must sign the artifact. See `ops/keys/reviewpack/README.md`.
3. **Key Rejected**: The signer's KeyID is not in `allowed_key_ids`.
   Update `ops/reviewpack_policy.toml` to include the KeyID.

## IF_FAIL: Bundle Verification

If `evidencepack verify` fails on a bundle input:

1. **Bad Bundle Version**: `BUNDLE_VERSION` file is missing or invalid.
2. **Manifest Checksum**: The bundle contents have been modified.
   The bundle is tamper-evident; any change invalidates the manifest.
3. **Inner Verification**: If the bundle structure is valid, the failure
   might be in the inner artifact verification (Signature/Policy).
   Use `--policy` or `--keys-dir` to override the bundled context if you
   suspect the bundled policy/keys are outdated or malicious.

## IF_FAIL: Audit Chain Verification (S10)

If `evidencepack audit verify <file>` or bundle verification reports audit failures:

1. **entry_hash mismatch**: An entry's content was modified after writing.
   The audit log has been tampered with. Investigate the change source.
2. **prev_hash mismatch**: The chain link is broken — an entry was
   inserted, deleted, or reordered. Restore from the last known-good backup.
3. **missing required field**: A log entry is malformed.
   May indicate a tool bug or manual editing.

### Recovery

- The audit log is append-only. Preserve the corrupt file for forensics.
- Restore from a known-good snapshot (e.g., from a verified bundle).
- Re-run `evidencepack audit verify <file>` to confirm the restored log is valid.
