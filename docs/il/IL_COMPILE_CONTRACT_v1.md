# IL Compile Contract v1

## Purpose
自然文要求を、実行可能かつ検証可能な IL（`docs/il/IL_CONTRACT_v1.md` 準拠）へ変換する compile 工程の契約を固定する。

## Version
- contract: `il_compile_contract_v1`
- output_contract: `IL_COMPILE_OUTPUT_v1` (logical)
- request_schema: `IL_COMPILE_REQUEST_v1`

## Scope
- 入力 envelope
- 出力 shape（success: `il/meta/evidence`、failure: `errors[]`）
- fail-closed 規約
- 決定論ノブ
- 観測成果物（obs artifacts）

## Non-Goals
- executor 本体の挙動定義（`IL_EXEC_CONTRACT_v1` で定義）
- LocalLLM 実装詳細（クライアント内部コード）
- CI 必須チェックの追加

## 1. Compile CLI Interface (S23-03 実装ターゲット)
```bash
python3 scripts/il_compile.py --request <request_json> --out <out_dir> [--model <model_name>] [--provider <rule_based|local_llm>] [--prompt-profile <v1|strict_json_v2|contract_json_v3>] [--seed <int>] [--no-fallback]
```

- MUST: `--request` は UTF-8 JSON ファイル
- MUST: `--out` に obs 成果物を出力
- MUST NOT: compile 成否を終了コードだけで表現しない（真実は `OK:/ERROR:/SKIP:` + report）
- MUST: `--provider local_llm` で失敗した場合、デフォルトは rule-based fallback（`--no-fallback` 指定時は fail-closed）

## 2. Input Envelope (`IL_COMPILE_REQUEST_v1`)

### Shape (MUST)
```json
{
  "schema": "IL_COMPILE_REQUEST_v1",
  "request_text": "natural language request",
  "context": {},
  "constraints": {
    "allowed_opcodes": [],
    "forbidden_keys": [],
    "max_steps": 8
  },
  "artifact_pointers": [
    {
      "path": "docs/il/examples/good_min.json",
      "sha256": "optional"
    }
  ],
  "determinism": {
    "temperature": 0.0,
    "top_p": 1.0,
    "seed": 7,
    "stream": false
  }
}
```

### Rules (MUST)
- `schema` MUST be `IL_COMPILE_REQUEST_v1`
- `request_text` MUST be non-empty string
- `artifact_pointers[].path` MUST follow `IL_CONTRACT_v1` path rule（repo-root relative, no absolute path, no `..`）
- `constraints.allowed_opcodes` がある場合、compile 出力はその集合の部分集合でなければならない
- `determinism` 未指定時は以下のデフォルトを強制:
  - `temperature=0.0`
  - `top_p=1.0`
  - `seed=7`
  - `stream=false`

## 3. Output Contract (`IL_COMPILE_OUTPUT_v1`)

Note:
- success payload には `schema` フィールドを追加しない（`IL_CONTRACT_v1` 互換を優先）
- failure payload は structured `errors[]` のみを返す

### Success Output (MUST)
成功時は `docs/il/IL_CONTRACT_v1.md` の成功形そのものを返す（`errors` は出さない）。

```json
{
  "il": {},
  "meta": {
    "version": "il_contract_v1"
  },
  "evidence": {}
}
```

### Failure Output (MUST)
失敗時は `il/meta/evidence` を返さず、structured `errors[]` のみを返す。

```json
{
  "errors": [
    {
      "code": "E_SCHEMA",
      "message": "non-empty string",
      "path": "/request_text",
      "hint": "provide request_text",
      "retriable": false
    }
  ]
}
```

### `errors[]` Item (MUST)
- `code`: `E_SCHEMA|E_INPUT|E_PROMPT|E_MODEL|E_PARSE|E_VALIDATE|E_FORBIDDEN|E_NONDETERMINISTIC|E_UNSUPPORTED`
- `message`: non-empty string
- `path`: optional JSON Pointer
- `hint`: optional remediation
- `retriable`: boolean

## 4. Fail-Closed Policy
- MUST: parse/validation/forbidden/determinism 逸脱のいずれかで `ERROR` にする
- MUST NOT: 失敗時に「それっぽいIL」を返さない
- MUST: model 返答が JSON でない場合は `E_PARSE`
- MUST: IL validator 不合格は `E_VALIDATE` で終了
- MUST: forbidden key（`timestamp`/`uuid`/`random` 等）検出時は `E_FORBIDDEN`

## 5. Determinism Rules
- MUST: decoding params を固定（`temperature=0.0`, `top_p=1.0`, `stream=false`）
- MUST: `seed` を明示し、report に記録
- MUST: prompt template version を固定し、report に `prompt_template_id` を記録
- MUST: artifact_pointers は `path` 昇順で解決して prompt に埋める
- MUST: 成功時の IL は `ILValidator` + `ILCanonicalizer` を通す
- MUST: canonical bytes hash（sha256）を report に残す

## 6. Observability Artifacts (MUST)
`--out` 配下に以下を出力する。

- `il.compile.report.json`（常に出力）
- `il.compile.request.normalized.json`（常に出力）
- `il.compile.prompt.txt`（常に出力）
- `il.compile.raw_response.txt`（常に出力）
- `il.compile.explain.md`（常に出力）
- `il.compiled.json`（success のみ）
- `il.compiled.canonical.json`（success のみ）
- `il.compile.error.json`（failure のみ）

`il.compile.report.json` 最小項目:
- `schema`: `IL_COMPILE_REPORT_v1`
- `status`: `OK|ERROR|SKIP`
- `error_count`: int
- `determinism`: `{temperature, top_p, seed, stream}`
- `prompt_template_id`: str
- `prompt_profile`: str
- `model`: str
- `provider_requested`: `rule_based|local_llm`
- `provider_selected`: `rule_based|local_llm`
- `fallback_used`: bool
- `canonical_sha256`: str（success のみ）
- `request_sha256`: str
- `prompt_sha256`: str
- `artifact_pointer_count`: int
- `compile_latency_ms`: int

## 7. Bridge to Execute (S23-03)
- success の `il.compiled.json` はそのまま `scripts/il_entry.py` の入力に渡せること
- failure の場合は execute を呼ばないこと（compile 段で停止）

Example:
```bash
python3 scripts/il_compile.py --request .local/compile_req.json --out .local/obs/compile_run
python3 scripts/il_entry.py .local/obs/compile_run/il.compiled.json --out .local/obs/exec_run
```
