# S6 Evidence Pack Specification (v1)

## 1. Overview
The **S6 Evidence Pack** (`evidence_pack_<TS>.tar.gz`) is a self-contained, verifiable artifact produced by the S5 pipeline. It is designed for third-party auditing without requiring access to the original source code repository.

## 2. File Format
- **Format**: `.tar.gz` (gzip-compressed tarball)
- **Naming Convention**: `evidence_pack_<TIMESTAMP>.tar.gz` (e.g., `evidence_pack_20260209T120000Z.tar.gz`)
- **Structure**:
    ```text
    ./
    ├── evidence_pack_v1     (Identity File, content: "1")
    ├── VERIFY_EVIDENCE.sh   (Bundled Verifier)
    ├── MANIFEST.txt         (Metadata & Checksums)
    ├── ops/gate1.sh         (Legacy Logic)
    ├── docs/rules/          (Validation Rules)
    │   ├── CHECKLIST-GATE-1.md
    │   └── GATE-1.md
    └── eval/results/
        └── latest.jsonl     (Evaluation Output)
    ```

## 3. Invariants
The following conditions MUST be met for a valid pack:

1.  **Identity**: Must contain `evidence_pack_v1` with content "1".
2.  **Format Version**: `MANIFEST.txt` must contain `format=v1`.
3.  **No Contamination**: Must NOT contain macOS metadata files (e.g., `._*`, `.DS_Store`).
4.  **Integrity**: All files listed in `MANIFEST.txt` must match their SHA256 checksums.
5.  **Self-Verification**: Must contain `VERIFY_EVIDENCE.sh` to self-validate.

## 4. Verification Procedure

### 4.1. Bundled Verification (Primary)
The pack contains its own verifier. Extract and run:

```bash
tar -xzf evidence_pack_*.tar.gz
cd evidence_pack_...
./VERIFY_EVIDENCE.sh
```

### 4.2. Repository Verification (Unified)
If you have the `ops` toolkit:

```bash
ops/verify_pack.sh <PACK_PATH>
```

### 4.3. Manual Verification
If scripts are unavailable:

1.  **Extract**: `mkdir -p /tmp/verify && tar -xzf <PACK> -C /tmp/verify`
2.  **Check Identity**: `cat /tmp/verify/evidence_pack_v1` -> "1"
3.  **Check Manifest**: `grep "format=v1" /tmp/verify/MANIFEST.txt`
4.  **Verify Checksums**:
    ```bash
    cd /tmp/verify
    sed -n '/--- sha256 checksums ---/,$p' MANIFEST.txt | tail -n +2 | sha256sum -c
    ```
5.  **Inspect Results**:
    Check `eval/results/latest.jsonl` for `"passed": true`.

## 5. Security & Reproducibility
- The pack is generated from a clean git state.
- `SUBMIT_HISTORY.sha256` (in `.local/reviewpack_artifacts/`) tracks the lineage of generated packs.
- `HEAD` in `MANIFEST.txt` links the pack to specific source code revision.

## 6. Legacy Compatibility (C10-FIX)
- **Review Pack Legacy Copy**: The build system produces a `review_pack_<TS>.tar.gz` alongside `review_bundle_<TS>.tar.gz`.
    - **Semantics**: This file is **File Name Compatible Only**.
    - **Content**: Accurate copy of the bundle. The internal root directory remains `review_bundle/`.
    - **Usage**: Use this if strictly required by toolchains expecting the filename pattern, but be aware of the internal `review_bundle` root.
