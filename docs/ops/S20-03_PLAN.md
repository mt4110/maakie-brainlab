# S20-03 Eval Wall v1 Implementation Plan

## Goal
Implement the minimal "Eval Wall v1" following S20-02 EVAL_SPEC_v1.
Focus on structure (dataset/artifacts) and auditable execution.

## User Review Required
> [!IMPORTANT]
> - `eval/run_eval.py` will be significantly refactored to support new artifact paths and strict taxonomy.
> - `dataset_id` will be introduced (defaulting to `seed-mini-v0001` if not present).

## Proposed Changes

### Data
#### [NEW] [data/eval/datasets/seed-mini-v0001/cases.jsonl](data/eval/datasets/seed-mini-v0001/cases.jsonl)
- Initial seed dataset adhering to `EVAL_SPEC_v1`.
#### [NEW] [data/eval/datasets/seed-mini-v0001/dataset.meta.json](data/eval/datasets/seed-mini-v0001/dataset.meta.json)
- Metadata for the seed dataset.

### Eval Logic
#### [MODIFY] [eval/run_eval.py](eval/run_eval.py)
- **Inputs**: Accept `dataset_id` (load from `data/eval/datasets/...`).
- **Outputs**: Write to `.local/rag_eval/runs/<run_id>/`.
  - `run.meta.json`, `results.jsonl`, `summary.json`.
- **Taxonomy**: Map internal failures to Frozen Failure Codes.
- **Run ID**: Generate `run__<utc>__<sha>__<dataset>__<config>`.

### Documentation
#### [MODIFY] [docs/ops/ROADMAP.md](docs/ops/ROADMAP.md)
- Update S20 section.

## Verification Plan

### Automated Tests
- `go test ./...` (Standard Gate)
- `python3 eval/run_eval.py --mode verify-only` (Verify run artifacts logic)

### Manual Verification
- Run `python3 eval/run_eval.py` (record mode) and check:
  - `.local/rag_eval/runs/` contains new run dir.
  - `results.jsonl` contains `status` and `failure_code`.
  - `summary.json` contains aggregation.
