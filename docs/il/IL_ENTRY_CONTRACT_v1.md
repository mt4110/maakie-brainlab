# IL Entry Contract v1

This document defines the strict contract for the single entry point `scripts/il_entry.py`.

## 1. Single Entry Law
All IL execution MUST go through `scripts/il_entry.py`. Legacy entry points like `il_exec_run.py`, `il_guard.py` etc., are deprecated. They should act as thin wrappers or emit SKIP messages directing users to `il_entry.py`.

## 2. Always Verify
Every execution MUST pass validation (canonicalization/guard) before proceeding to execution.
- If validation fails, the process MUST print `ERROR: ...` and set an internal `STOP=1` (or equivalent flag).
- `execute` MUST NOT run if validation fails.

## 3. Execution Safety (Stopless)
- The script MUST NOT use `sys.exit()`, `raise SystemExit`, or `assert`.
- Internal exceptions MUST be caught and printed as `ERROR: ...`.
- Interruption or validation failures MUST log clearly and proceed to a natural exit.
- The return code should NOT be relied upon for control flow; the truth is in the text logs.

## 4. Evidence (Observation Logs)
- Regardless of success or failure, an OBS log MUST be written using `OBS_FORMAT_v1`.
- Standard output must summarize the status with `OK:`, `ERROR:`, or `SKIP:` prefixes to be grep-friendly.

## 5. CLI Interface
```bash
python3 scripts/il_entry.py <il_path> --out <out_dir> [--fixture-db <path>]
```
