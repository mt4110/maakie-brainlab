# EVAL_SPEC v1
- Purpose: tuning結果を再現可能にする（入力/出力/判定の固定）
- Fixed: dataset format, failure taxonomy, run output naming

## Eval Wall v1 — dataset + run artifacts + failure taxonomy (frozen)

### 1) Dataset (fixed inputs)

#### Dataset location (repo)
- Root directory: `data/eval/datasets/`
- Each dataset MUST live in:
  - `data/eval/datasets/<dataset_id>/`
- Each dataset directory MUST contain:
  - `cases.jsonl` (required)
  - `dataset.meta.json` (required)
  - `README.md` (optional but recommended)

#### dataset_id rules (frozen)
- Format: `rag-eval-wall-v1__<name>__vNNNN`
  - `<name>`: `[a-z0-9-]+` (kebab-case)
  - `vNNNN`: zero-padded integer version (e.g., `v0001`)
- dataset_id is immutable once published:
  - Additions/changes MUST create a NEW dataset_id (bump `vNNNN`)
  - Never mutate an existing dataset directory after it is referenced by a run

#### cases.jsonl schema (frozen)
Each line is one JSON object with required fields:

- `case_id` (string, required)
  - Unique within the dataset
  - Immutable once published
- `query` (string, required)
- `expectation` (object, required)
  - Minimal recommended keys:
    - `must_answer` (bool) — whether the system should answer (vs refuse)
    - `must_cite` (bool) — whether citations/evidence are required
    - `keywords` (array of string, optional) — expected concepts
- `tags` (array of string, required)
  - For aggregation (e.g., `["japanese", "injection", "multi-hop"]`)
- `notes` (string, optional)

`dataset.meta.json` MUST include:
- `dataset_id` (string)
- `eval_spec_version` (string, MUST be `EVAL_SPEC_v1`)
- `created_utc` (string, ISO-8601, informational)
- `source` (string, informational; can be "synthetic" etc.)

### 2) Run artifacts (fixed outputs)

#### Run output location (local artifact)
- Root directory: `.local/rag_eval/runs/`
- Each run MUST write to:
  - `.local/rag_eval/runs/<run_id>/`

NOTE:
- `.local/` is local-only; artifacts are not committed by default.
- If a run must be referenced in PR evidence, include a log path in PR body, but do NOT paste absolute paths into docs.

#### run_id rules (stable keys)
- Format: `run__<utc>__<gitsha7>__<dataset_id>__<confighash8>`
  - `<utc>`: `YYYYMMDDTHHMMSSZ`
  - `<gitsha7>`: git commit short SHA (7)
  - `<confighash8>`: first 8 chars of SHA-256 of canonical config JSON (see `run.meta.json`)
- Two runs are comparable when:
  - `dataset_id` matches
  - `confighash` matches
  - `eval_spec_version` matches

#### Minimal file set (MUST)
Each run directory MUST contain:
- `run.meta.json` (required)
  - MUST include:
    - `run_id`, `dataset_id`, `eval_spec_version`
    - `git_commit`
    - `config.canonical_json` (string) and `config.sha256` (string)
- `results.jsonl` (required)
  - One line per `case_id`
  - MUST include:
    - `case_id`, `status`, `failure_code` (nullable), `latency_ms` (optional)
- `summary.json` (required)
  - Aggregated counts by `status` and `failure_code`
- `stdout.log` (recommended)
- `command.txt` (recommended; the exact command line used)

### 3) Failure taxonomy (fixed labels)

Failure codes are **frozen identifiers** for aggregation.
- Format: uppercase ASCII + underscore (e.g., `RETRIEVAL_EMPTY`)
- Once published, codes MUST NOT be renamed or deleted.
- New codes may be added, but only when clearly non-overlapping.

#### Status and failure_code
- `status` MUST be one of:
  - `PASS`
  - `FAIL`
  - `SKIP`
- `failure_code` is:
  - `null` when `status=PASS`
  - one of the following when `status=FAIL`

#### failure_code list (v1)
- `DATASET_INVALID` — dataset schema violation / missing required fields
- `FORMAT_INVALID` — output not machine-parseable as required
- `RETRIEVAL_EMPTY` — retrieval returned no usable context
- `RETRIEVAL_OFFTOPIC` — retrieved context is irrelevant to query (judged by rule/heuristic or evaluator)
- `ANSWER_UNSUPPORTED` — answer is not supported by retrieved context
- `CITATION_MISSING` — required citation/evidence missing
- `REFUSAL_MISSING` — should refuse but answered
- `REFUSAL_UNNECESSARY` — refused but should answer
- `INJECTION_SUCCEEDED` — followed prompt injection / untrusted instruction
- `TIMEOUT` — exceeded run time budget
- `CRASH` — unhandled error / panic / exception

#### Tagging rule (short, frozen)
- Choose the **most primary** failure cause per case (one failure_code).
- Do not stack multiple codes in v1 (aggregation simplicity > nuance).
