# IL Thread Runner v2 Contract

## Purpose
`compile -> il_entry` を単一のスレッド実行導線として固定し、`validate-only` と `run` の振る舞いを決定論的に定義する。

## Version
- contract: `il_thread_runner_v2_contract`
- runner_summary_schema: `IL_THREAD_RUNNER_V2_SUMMARY_v1`
- runner_case_schema: `IL_THREAD_RUNNER_V2_CASE_v1`

## CLI
```bash
python3 scripts/il_thread_runner_v2.py \
  --cases <cases.jsonl> \
  --mode <validate-only|run> \
  --out <out_dir> \
  [--provider <rule_based|local_llm>] \
  [--model <model_name>] \
  [--prompt-profile <v1|strict_json_v2|contract_json_v3>] \
  [--seed <int>] \
  [--no-fallback]
```

## Input Cases (`cases.jsonl`)
1行1case。各行は以下:

```json
{
  "id": "case_id",
  "request": {
    "schema": "IL_COMPILE_REQUEST_v1",
    "request_text": "search alpha",
    "context": {},
    "constraints": {},
    "artifact_pointers": [],
    "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": false}
  },
  "fixture_db": "tests/fixtures/il_exec/retrieve_db.json"
}
```

Rules:
- MUST: `id` は non-empty string
- MUST: `request` は object
- MAY: `fixture_db` は省略可能
- MUST NOT: invalid line で runner 全体を中断しない（そのcaseを `compile_status=ERROR` 扱い）

## Mode Contract
- `validate-only`:
  - MUST: compile のみ実行
  - MUST NOT: `il_entry` / executor を呼ばない
  - MUST: `entry_status=SKIP` と理由を case record に残す
- `run`:
  - MUST: compile 実行後、compile成功ケースのみ `il_entry` を実行
  - MUST: compile失敗ケースは `entry_status=SKIP`（fail-closed）

## Fail-Closed Policy
- compile が `ERROR` の case は `il_entry` を実行してはならない
- 失敗時は `errors[]` を保持し、`il.compiled.json` を生成しない
- stopless: 他caseへ継続し、最終 summary に集計する

## Artifacts
`--out` 配下:

- `cases.jsonl`（全caseの集計行）
- `summary.json`
- `cases/<id>/compile/`
  - `il.compile.report.json`
  - `il.compile.request.normalized.json`
  - `il.compile.prompt.txt`
  - `il.compile.raw_response.txt`
  - `il.compiled.json` / `il.compiled.canonical.json`（compile成功時のみ）
  - `il.compile.error.json`（compile失敗時のみ）
- `cases/<id>/entry/`（runモードかつcompile成功時のみ）
  - `il.exec.report.json` 等の `il_entry` 成果物

## Case Record (`IL_THREAD_RUNNER_V2_CASE_v1`)
最低必須フィールド:
- `schema`: `IL_THREAD_RUNNER_V2_CASE_v1`
- `id`: case id
- `mode`: `validate-only|run`
- `compile_status`: `OK|ERROR`
- `entry_status`: `OK|ERROR|SKIP`
- `compile_error_codes`: array[string]
- `entry_stop`: 0 or 1
- `artifacts`: relative paths object

## Summary (`IL_THREAD_RUNNER_V2_SUMMARY_v1`)
最低必須フィールド:
- `schema`: `IL_THREAD_RUNNER_V2_SUMMARY_v1`
- `mode`
- `provider`
- `model`
- `prompt_profile`
- `seed`
- `allow_fallback`
- `total_cases`
- `compile_ok_count`
- `compile_error_count`
- `entry_ok_count`
- `entry_error_count`
- `entry_skip_count`
- `error_count`
- `sha256_cases_jsonl`

## Determinism
- 同一 `cases.jsonl` + 同一 flags + 同一 code で、`cases.jsonl` の sha256 は一致しなければならない
- case record は入力順で固定する
- case record には run時刻等の非決定値を入れない
