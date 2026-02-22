# IL_ENTRY_CONTRACT_v1

## Purpose
Unify IL execution into a single, predictable entry point that always enforces validation and verification.

## Interface
- **Command**: `python3 scripts/il_entry.py <il_path> --out <out_dir> [--fixture-db <path>]`
- **Control Flow**: STOPLESS. The script must never use `sys.exit()` or unhandled exceptions to terminate.
- **Log Format**: Every step must output exactly one of:
  - `OK: <message>`
  - `ERROR: <message>`
  - `SKIP: <message>`

## Execution Sequence
1. **ENVIRONMENT**: Check repository root and dependency health.
2. **VALIDATE**: Use `ILValidator` to check schema and invariants.
3. **CANONICALIZE**: Use `ILCanonicalizer` to produce a stable version of the IL.
4. **EXECUTE**: Use `src/il_executor.py:execute_il` for opcode processing.
5. **VERIFY**: Check output artifacts for existence and basic schema validity.

## Result Artifacts
- **report.json**: A unified result summarizing all steps.
- **logs**: Standard output and error captured for auditing.

## Error Handling
If any step produces an `ERROR`, set `STOP=1`. Subsequent steps must be `SKIP`ed with a clear reason.
