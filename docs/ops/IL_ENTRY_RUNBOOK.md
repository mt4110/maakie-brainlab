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

## Decision Playbooks (S32-23)

### Playbook A: compile parse failure (`E_PARSE`)
- 確認コマンド:
  - `python3 -m unittest -v tests/test_s32_compile_parse_repair_v3.py`
  - `python3 scripts/il_compile.py --request <req.json> --out <compile_out> --provider local_llm --no-fallback`
- 判断条件:
  - `il.compile.error.json` に `E_PARSE` が含まれる
  - `il.compile.report.json` の `repair_applied=false` か `repair_rule_id=""`
- 次アクション:
  - prompt/profile を `strict_json_v2` または `contract_json_v3` へ固定して再試行
  - 修復対象外フォーマットは fail-closed のままケース隔離

### Playbook B: no-hit (`E_RAG_NO_HIT`)
- 確認コマンド:
  - `python3 scripts/il_exec.py tests/fixtures/il_exec/il_rag_min.json --out <exec_out> --fixture-db tests/fixtures/il_exec/retrieve_db.json`
  - `python3 scripts/ops/s32_retrieval_eval_wall.py --cases tests/fixtures/s32_05/retrieval_eval_cases.jsonl`
- 判断条件:
  - `il.exec.report.json` の `error_codes` に `E_RAG_NO_HIT`
  - retrieval wall の `hit_rate_at_k` が基準未達
- 次アクション:
  - `COLLECT` source/path と policy filter 設定を再確認
  - query terms を追加し `SEARCH_RAG` の `max_docs` を増やして再評価

### Playbook C: lock conflict (`E_ARTIFACT_LOCK`)
- 確認コマンド:
  - `python3 scripts/il_thread_runner_v2.py --cases <cases.jsonl> --mode validate-only --out <run_out>`
  - `python3 scripts/il_thread_runner_v2_orchestrator.py --cases <cases.jsonl> --mode validate-only --out <orch_out> --shard-count 2`
- 判断条件:
  - runner ログに `E_ARTIFACT_LOCK` が出現
  - `.artifact.lock.json` が stale かつ cleanup 不能
- 次アクション:
  - stale lock を除去後に再実行
  - out_dir を shard ごとに分離して同時実行を回避

### Playbook D: retry saturation
- 確認コマンド:
  - `python3 -m unittest -v tests/test_s32_retry_policy_matrix.py`
  - `python3 scripts/il_thread_runner_v2_doctor.py --run-dir <run_out>`
- 判断条件:
  - `summary.json` の `retries_used_count` / `retry_attempts_total` が高止まり
  - `retry_final_reason_histogram` が特定 reason に偏る
- 次アクション:
  - non-retriable reason (`E_ENTRY_PROTOCOL` 等) は入力/実装を修正し再試行を止める
  - retriable reason (`E_TIMEOUT` 等) は timeout/backoff と entry 実装を見直す

### Playbook E: latency breach
- 確認コマンド:
  - `python3 scripts/ops/s32_latency_slo_guard.py --run-dir <run_out>`
  - `python3 scripts/ops/s32_operator_dashboard_export.py --run-dir <run_out>`
- 判断条件:
  - latency guard の `status` が `WARN/ERROR`
  - `p95_latency_ms` が budget 超過
- 次アクション:
  - worst case の compile report を抽出して request 複雑度/artifact 数を削減
  - profile auto-select の閾値を見直し高複雑度ケースを厳格 profile に寄せる
