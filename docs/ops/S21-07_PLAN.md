# S21-07: IL optional hardening (log prefix + pure JSON reports)

## Goal
Harden IL scripts (specifically `il_exec.py`) to produce machine-parsable logs and strict JSON reports.

## Absolute Rules
- Shell: `exit`/`return` non-zero/`set -e` PROHIBITED.
- Python: `sys.exit` / `raise SystemExit` PROHIBITED.
- Output: `OK:` / `ERROR:` / `SKIP:` prefixes for all log lines.
- JSON: `allow_nan=False`. NaN/Infinity strings PROHIBITED (must be `null`).

## Affected Files
- `scripts/il_exec.py`

## Plan
1.  **Log Formatting**:
    -   Modify `log()` function or print statements to enforce `OK:` / `ERROR:` / `SKIP:` prefixes.
    -   Standardize log messages for opcodes (NOOP, etc.).

2.  **JSON Hardening**:
    -   In `write_exec_report`:
        -   Traverse the data structure.
        -   Convert `float('nan')`, `float('inf')`, `float('-inf')` to `None`.
        -   Call `json.dump(..., allow_nan=False)`.
        -   Log `OK: Report saved` or `ERROR: Report save failed`.

3.  **Verification**:
    -   Run `make verify-il` to ensure no regressions.
    -   Manual check of log output and generated JSON.

## Verification Plan
### Automated
- `make verify-il`

### Manual
- Inspect `il.exec.json` for `null` values where NaN might have been.
- Inspect console output for `OK:` / `ERROR:` / `SKIP:` prefixes.
