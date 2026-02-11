# Evidence Retention Policy

## Store Layout
The evidence store is located at `.local/evidence_store/` (default).

```text
.local/evidence_store/
  index/
    packs.tsv   # Append-only log of all created packs
  packs/
    <kind>/
      evidence_<kind>_<UTC>_<gitsha>.tar.gz
  tmp/          # Staging area for atomic writes
```

## Index Format (`index/packs.tsv`)
Tab-separated values (TSV). Headerless (or with header in first line, tool decision).
Columns: `created_at_utc`, `kind`, `filename`, `git_sha`, `sha256`, `size_bytes`.

## Retention Rules
Defined in `ops/evidence_retention.json`.
- **Max Total Bytes**: Soft limit for the entire store.
- **Keep Last N**: Minimum number of packs to keep per kind.
- **Max Age Days**: Maximum age of packs to keep.

## Garbage Collection (GC)
The `gc` command cleans up old packs based on retention rules.

### Safety Contract
- **Default: Dry-Run**: `evidencepack gc` WITHOUT flags MUST only list deletion candidates. It MUST NOT delete anything.
- **Explicit Apply**: Deletion only happens with `evidencepack gc --apply`.
- **Packs Only**: GC MUST only delete files in `packs/`. It MUST NEVER delete `index/` files or the `index` directory itself.
- **Audit Log**: A `gc.log` may be appended to record deletions.
