# IL Executor Contract v1

## Purpose

IL executor が出力する **report** と **result** の契約を固定する。
executor は「嘘をつかない」ことだけに全振りする。

---

## Report: `il.exec.report.json`

**MUST**: 常に出力する（例外が出ても出す）。

### Schema

```json
{
  "schema": "IL_EXEC_REPORT_v1",
  "overall_status": "OK | ERROR | SKIP",
  "steps": [
    {
      "index": 0,
      "opcode": "SEARCH_TERMS",
      "status": "OK | ERROR | SKIP",
      "reason": "non-empty string",
      "in_summary": {},
      "out_summary": {}
    }
  ]
}
```

### Fields (MUST)

| Field | Type | Rule |
|---|---|---|
| `schema` | str | MUST be `"IL_EXEC_REPORT_v1"` |
| `overall_status` | str | MUST be one of `"OK"`, `"ERROR"`, `"SKIP"` |
| `steps` | array | MUST contain one entry per opcode step |
| `steps[].index` | int | 0-based step index |
| `steps[].opcode` | str | opcode name from IL |
| `steps[].status` | str | MUST be one of `"OK"`, `"ERROR"`, `"SKIP"` |
| `steps[].reason` | str | MUST be non-empty |
| `steps[].in_summary` | dict/str | summary of input seen by this step |
| `steps[].out_summary` | dict/str | summary of output produced by this step |

### overall_status Determination (MUST)

1. steps に `ERROR` が1つでもあれば → `"ERROR"`
2. ERROR がなく `OK` が1つでもあれば → `"OK"`
3. 全部 `SKIP` なら → `"SKIP"`

---

## Result: `il.exec.result.json`

**MUST**: `overall_status == "OK"` のときだけ出力する。
**MUST NOT**: `overall_status` が `"ERROR"` または `"SKIP"` のとき出力してはならない。

### Schema

```json
{
  "schema": "IL_EXEC_RESULT_v1",
  "answer": "",
  "cites": []
}
```

### Fields (MUST)

| Field | Type | Rule |
|---|---|---|
| `schema` | str | MUST be `"IL_EXEC_RESULT_v1"` |
| `answer` | str | deterministic summary string（empty許容） |
| `cites` | array | deterministic order; P2 では空でもOK |

---

## Opcodes (P2/S31 v1)

| Opcode | P2 Behavior |
|---|---|
| `SEARCH_TERMS` | `il.search_terms` が list[str] なら OK。なければ SKIP |
| `RETRIEVE` | fixture DB からルックアップ。fixture なければ SKIP |
| `ANSWER` | retrieved docs から deterministic answer を生成。docsなしなら SKIP |
| `CITE` | retrieved docs から cite_key を生成。docs なければ SKIP |
| `COLLECT/NORMALIZE/INDEX/SEARCH_RAG/CITE_RAG` | deterministic RAG bridge（fixture中心） |

## Opcode Args Guard

- 各 opcode の `args` は型検証される（不正時は `ERROR`）。
- unknown arg key は `E_OPCODE_ARGS` として fail-closed。
