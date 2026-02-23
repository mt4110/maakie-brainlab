# IL Entry Runbook

This runbook outlines the operational procedures for using the IL single entry point.

## 1. Primary Entry Point
Do not use legacy entry points. Always use `scripts/il_entry.py`.
```bash
python3 scripts/il_entry.py <path/to/il.json> --out <OBS_DIR>
```

## 2. Verification (Light / Smoke)
To verify the health of the IL entry system without running heavy evaluations, use the smoke test:
```bash
python3 tests/test_il_entry_smoke.py
```
- It runs two cases: a valid IL and an invalid IL.
- It does NOT use `assert` or terminate with errors (stopless).
- It outputs `OK:` or `ERROR:` logs for verification via grep.

## 3. Grep Rules for Audit
To audit execution results, rely on standard output and observation logs. Do NOT rely on exit codes.
- `^OK:` - Indicates successful validation and execution.
- `^ERROR:` - Indicates a clear validation failure or runtime exception. Downstream operations are skipped.
- `^SKIP:` - Indicates intentionally skipped operations (e.g., legacy scripts warning).
