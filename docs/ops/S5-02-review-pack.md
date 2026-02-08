# S5-02 Review Pack

## Overview
This automated process (S5-02) consolidates the "HEAD confirmation" process. It ensures that a specific git HEAD, its evaluation results, and validation logs are bundled together in a reproducible way.

## Usage

### Creating a Review Pack
To generate a review pack, run:

```bash
make s5
```

This will:
1.  Verify the git repository is clean.
2.  Run `make gate1` (including environment checks, unit tests, and evaluation).
3.  Package the results, `gate1.sh`, `docs/rules`, and `VERIFY` (if present) into a `tar.gz` archive.
4.  Update `SUBMIT_HISTORY.sha256` with the pack's SHA256, filename, HEAD, timestamp, and result source.

**Output Location:** `.local/reviewpack_artifacts/review_pack_<TIMESTAMP>.tar.gz`

### Verifying a Review Pack
To verify a review pack, run:

```bash
make s5-verify PACK=<path_to_pack>
```

Example:
```bash
make s5-verify PACK=.local/reviewpack_artifacts/review_pack_20260208T142021Z.tar.gz
```

This will:
1.  Check if the pack file exists.
2.  Verify that the `head` in the pack's manifest matches the current repository `HEAD`.
3.  Verify the SHA256 checksums of all files included in the pack.

## Troubleshooting

-   **"Git working tree is dirty"**: Commit or stash your changes before running `make s5`.
-   **"Gate-1 failed"**: Check the log file indicated in the error message for details on why the tests or evaluation failed.
-   **"Pack HEAD ... does not match current repo HEAD"**: When verifying, ensure you have checked out the specific commit that was used to generate the pack.
