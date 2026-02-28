# IL Entry Runbook v2

## Quickstart (3 commands)

```bash
python3 scripts/il_workspace_init.py --out .local/obs/il_ws --force
python3 scripts/il_compile.py --request .local/obs/il_ws/request.sample.json --out .local/obs/il_ws/out/compile
python3 scripts/il_entry.py .local/obs/il_ws/out/compile/il.compiled.json --out .local/obs/il_ws/out/entry --fixture-db tests/fixtures/il_exec/retrieve_db.json
```

## Unified CLI (`ilctl`)

```bash
python3 scripts/ilctl.py --help
python3 scripts/ilctl.py init --out .local/obs/il_ws --force
python3 scripts/ilctl.py doctor --out .local/obs/il_doctor
```

## Primary Entry Rules

- Do not use legacy entrypoints. Always use `scripts/il_entry.py`.
- Compile failures are fail-closed. Do not run entry when compile is `ERROR`.
- For automation and smoke checks, rely on grep-friendly logs (`OK:`, `ERROR:`, `SKIP:`).

## Decision Tree

### 1) `il_compile.py` failed

1. Inspect `il.compile.error.json` and `il.compile.report.json`.
2. If `E_SCHEMA`/`E_NONDETERMINISTIC`: fix request JSON.
3. If `E_MODEL`/`E_PARSE`: retry with `--provider rule_based` or keep fallback enabled.
4. Re-run compile and confirm `OK: phase=end STOP=0`.

### 2) `il_entry.py` failed

1. Inspect `il.exec.report.json` and stdout (`phase=end STOP=1`).
2. Confirm IL passes lint: `python3 scripts/il_lint.py --il <il.json>`.
3. Confirm fixture path exists when using `RETRIEVE`.
4. Re-run entry with explicit `--out` and capture logs.

### 3) `il_thread_runner_v2.py` failed

1. Inspect `summary.json` and `failure_digest.json`.
2. Use quarantine to isolate problematic cases:
   - `--exclude-case-id <id>` or `--exclude-file <ids.txt>`
3. Resume from partial output after fixing blockers:
   - `--resume`
4. For large case sets, use shard execution:
   - `--shard-index <n> --shard-count <N>`
   - merge with `scripts/il_thread_runner_v2_merge.py`

## Operational Commands

### Format / Lint

```bash
python3 scripts/il_fmt.py --check docs/il/examples/*.json
python3 scripts/il_lint.py --il tests/fixtures/il_exec/il_min.json --out .local/obs/il_lint.report.json
```

### Compile / Entry

```bash
python3 scripts/il_compile.py --request <req.json> --out <compile_out>
python3 scripts/il_entry.py <compile_out>/il.compiled.json --out <entry_out> --fixture-db tests/fixtures/il_exec/retrieve_db.json
```

### Thread Runner

```bash
python3 scripts/il_thread_runner_v2.py --cases <cases.jsonl> --mode run --out <run_out>
python3 scripts/il_thread_runner_v2_doctor.py --run-dir <run_out>
```

### Doctor

```bash
python3 scripts/il_doctor.py --out .local/obs/il_doctor
```

## Troubleshooting by Error Family

- `E_SCHEMA`: request/IL shape invalid. Validate JSON structure first.
- `E_NONDETERMINISTIC`: determinism knobs violated (`temperature/top_p/stream`).
- `E_PARSE`: model response parse failure. Inspect `il.compile.raw_response.txt`.
- `E_VALIDATE`: IL contract violation after compile.
- `E_RETRIEVE_*`: fixture/index/doc mismatch in retrieve phase.
- `E_ENTRY_*`: entry subprocess protocol/timeout/artifact issues.

## Audit Notes

- Truth is in text logs and artifacts, not exit codes alone.
- Minimum artifacts per compile run:
  - `il.compile.report.json`
  - `il.compile.error.json` or `il.compiled.json`
  - `il.compile.explain.md`
- Minimum artifacts per runner run:
  - `cases.jsonl`, `summary.json`, `failure_digest.json`
