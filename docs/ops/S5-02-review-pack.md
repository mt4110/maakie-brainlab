# S5-02 Review Pack Pipeline

## Overview
This automated process (S5-02) consolidates the "HEAD confirmation" process. It ensures that a specific git HEAD, its evaluation results, and validation logs are bundled together in a reproducible way.

## Usage

### Creating an Evidence Pack
To generate an evidence pack (formerly review pack), run:

```bash
make s5
```

This will:
1.  Verify the git repository is clean.
2.  Run `make gate1` (including environment checks, unit tests, and evaluation).
3.  Package the results, `gate1.sh`, `docs/rules`, and `VERIFY_EVIDENCE.sh` into a `tar.gz` archive.
4.  Update `SUBMIT_HISTORY.sha256` with the pack's SHA256, filename, HEAD, timestamp, and result source.

**Output Location:** `.local/reviewpack_artifacts/evidence_pack_<TIMESTAMP>.tar.gz`

### Creating a Review Bundle
To generate a comprehensive review bundle (with source snapshot):

```bash
go run cmd/reviewpack/main.go pack
```

**Output Location:** `review_bundle_<TIMESTAMP>.tar.gz`

### Verifying a Pack (Unified)
To verify ANY pack type (Evidence, Review Bundle, or Legacy), use the unified target:

```bash
make verify-pack PACK=<path_to_pack>
```
(Or run `bash ops/verify_pack.sh <PACK>` directly)

This will:
1.  **Detect Identity**: Check for `evidence_pack_v1` or `review_pack_v1`.
2.  **Dispatch Verifier**: Run the bundled `VERIFY_EVIDENCE.sh` or `VERIFY.sh`.
3.  **Verify Integrity**: Ensure all checksums match `MANIFEST.txt` (or `.tsv`).

## Troubleshooting

-   **"Git working tree is dirty"**: Commit or stash your changes before running `make s5`.
-   **"Gate-1 failed"**: Check the log file indicated in the error message for details.
-   **"Unknown pack format"**: Ensure the pack contains a valid identity file (`evidence_pack_v1` or `review_pack/review_pack_v1`).
