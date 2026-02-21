# DETERMINISTIC_PLAN_TEMPLATE (v1)

## Goal
- {{GOAL_ONE_LINE}}

## Invariants (Must Hold)
- Planは分岐と停止条件（嘘をつかない）
- Canonicalは1回だけ固定（以降はObservations）
- skipは理由1行、errorはその場で停止
- 編集対象は実パス固定（探索→確定→記録）

## Inputs (SOT)
- {{SOT_PATHS}}

## Outputs (Deliverables)
- {{DELIVERABLES}}

## Gates
- make test PASS
- go run cmd/reviewpack/main.go submit --mode verify-only PASS

## Phase 0 — Scope Definition (STOP条件つき)
- if scope missing:
  - error: "scope missing; define explicitly before coding"

## Phase 1 — Define Deliverables
- Deliverable A: {{A}}
- Deliverable B: {{B}}

## Phase 2 — Implementation
- smallest safe steps + local gates

## Phase 3 — Final Gate & Canonical Pin (single)
- pin once: commit / bundle / sha256
- note: future verify-only outputs are Observations

## Phase 4 — PR Ritual
- Canonical block is written exactly once

## IL-planned RAG/Satellite (No hidden RAG)

### Purpose

RAG must NOT run "in the background".
All retrieval must be observable as an IL procedure with artifacts:
COLLECT -> NORMALIZE -> INDEX -> SEARCH -> CITE

### Non-negotiable rules

- No exit/return non-zero, no set -e, no trap EXIT.
- No sys.exit / SystemExit / assert.
- Exceptions are allowed only as *captured diagnostics*:
  print("ERROR: ...") and set STOP=1. Never crash-control the workflow.
- Deterministic ordering MUST be explicit in every artifact.

### Opcode set (minimum for S22-04)

- COLLECT: ingest sources -> content-addressed blobs + manifest
- NORMALIZE: canonicalize text -> normalized texts + manifest
- INDEX: build deterministic index -> index.json + meta
- SEARCH: deterministic query -> ranked results.jsonl
- CITE: stable citations -> citations.jsonl + citations.md

### Artifact spec (minimum)

All outputs go under run-scoped obs_dir:
- obs_dir: .local/obs/s22-04_*/   (run name contains UTC timestamp only)

#### COLLECT

- 10_collect_manifest.jsonl
  - one line per doc (stable sorted):
    {"doc_id":"sha256:...","src":"<repo-rel-path or uri>","size":1234}
- 11_collect_blobs/<doc_id>.bin (or .txt when already text)

#### NORMALIZE

- 20_norm_manifest.jsonl (sorted by doc_id asc)
- 21_norm_text/<doc_id>.txt (utf-8, newline normalized)

#### INDEX (v0: lightweight)

- 30_index_meta.json (counts, version, tokenizer rules)
- 31_index.json
  - deterministic structure (sorted keys, stable arrays)
  - avoid heavy vector DB for now

#### SEARCH

- 40_search_query.json (query terms + options)
- 41_search_results.jsonl
  - stable tie-break:
    score desc, doc_id asc, then offset asc

#### CITE

- 50_citations.jsonl
  - {"doc_id":"...","excerpt":"...","offset":123,"reason":"..."}
- 51_citations.md (human-readable)

### Determinism rules

- All manifests/results must be sorted with explicit rules.
- Truncation must be deterministic:
  excerpt_max_chars = fixed constant in code (documented in meta).
- Prefer repo-relative paths to avoid host leakage.
- No timestamps inside file bodies (timestamps only in obs_dir name).

### STOPLESS control flow (pseudo-code)

```python
STOP = 0

for step in [COLLECT, NORMALIZE, INDEX, SEARCH, CITE]:
    if STOP == 1:
        log("SKIP: blocked by previous ERROR step=" + step)
        continue

    try:
        run(step)
        if not artifacts_exist_and_valid(step):
            log("ERROR: step failed step=" + step + " reason=missing_or_invalid_artifacts")
            STOP = 1
        else:
            log("OK: step succeeded step=" + step)
    catch Exception as e:
        log("ERROR: exception captured step=" + step + " err=" + str(e))
        STOP = 1
```

### DoD (Design-ready for implementation)

- IL contract includes the five opcodes with their required fields
- Artifact names/spec are written (this section)
- Task plan includes path discovery (no guessing) and split-heavy execution
