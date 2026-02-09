# S6 Evidence Pack Specification (v1)

## 1. Overview
The **S6 Evidence Pack** is a self-contained, verifiable artifact produced by the S5 pipeline. It is designed for third-party auditing without requiring access to the original source code repository.

## 2. File Format
- **Format**: `.tar.gz` (gzip-compressed tarball)
- **Naming Convention**: `review_pack_<TIMESTAMP>.tar.gz` (e.g., `review_pack_20231027T012345Z.tar.gz`)
- **Structure**:
    ```text
    ./
    ├── MANIFEST.txt         (Metadata & Checksums)
    ├── ops/gate1.sh         (Execution Logic)
    ├── docs/rules/          (Validation Rules)
    │   ├── CHECKLIST-GATE-1.md
    │   └── GATE-1.md
    └── eval/results/
        └── latest.jsonl     (Evaluation Output)
    ```

## 3. Invariants
The following conditions MUST be met for a valid pack:

1.  **Format Version**: `MANIFEST.txt` must contain `format=v1`.
2.  **No Contamination**: Must NOT contain macOS metadata files (e.g., `._*`, `.DS_Store`).
3.  **Integrity**: All files listed in `MANIFEST.txt` must match their SHA256 checksums.
4.  **Completeness**: Use of `check_required_paths` in verification ensures critical files exist.

## 4. Verification Procedure

### 4.1. Automated Verification (Recommended)
Use the standalone verification script provided in the ops toolkit:

```bash
bash ops/s6_verify_pack.sh <PACK_PATH>
```

### 4.2. Manual Verification
If the script is unavailable, perform these steps:

1.  **Extract**: `mkdir -p /tmp/verify && tar -xzf <PACK> -C /tmp/verify`
2.  **Check Manifest**: Verify `grep "format=v1" /tmp/verify/MANIFEST.txt`
3.  **Verify Checksums**:
    ```bash
    cd /tmp/verify
    sed -n '/--- sha256 checksums ---/,$p' MANIFEST.txt | tail -n +2 | sha256sum -c
    ```
4.  **Inspect Results**:
    Check `eval/results/latest.jsonl` for `"passed": true` and `"has_sources": true`.

## 5. Security & Reproducibility
- The pack is generated from a clean git state.
- `SUBMIT_HISTORY.sha256` (in the artifacts directory) tracks the lineage of generated packs.
- `HEAD` in manifest links the pack to specific source code revision.
