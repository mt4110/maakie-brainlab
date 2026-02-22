# IL_ENTRY_RUNBOOK

## Overview
`scripts/il_entry.py` is the primary entry point for all IL execution in the repository. It ensures that every IL run is validated, canonicalized, and verified.

## Standard Execution
To run an IL file:
```bash
python3 scripts/il_entry.py path/to/il.json --out .local/obs/run_name
```

## Smoke Verification
To quickly check if the entry point and core logic are functional:
```bash
python3 scripts/il_entry_smoke.py
```
This script runs a good and bad case and produces a summary. It never exits with a non-zero code.

## Full Diagnostics
If a run fails, examine the directory specified by `--out`:
- `canonical.il.json`: The stable version of your IL.
- `il.exec.report.json`: The detailed execution report.
- Standard output logs: Check for `ERROR:` lines to identify the first failing step.

## Policy
1. **Never use legacy runners** (like `scripts/il_exec_run.py`) directly for production or CI. Always go through `il_entry.py`.
2. **Never commit IL binaries**: Only commit the JSON sources. The entry point handles canonicalization.
