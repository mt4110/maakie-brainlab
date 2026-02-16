# S20-03 Task — Eval Wall v1 (Minimal)

## Progress
- 0% Start
- 30% Dataset skeleton
- 60% Run artifacts writer
- 80% Taxonomy wiring
- 90% Gates pass
- 100% PR created

## C0: Safety Snapshot
- [ ] `git status -sb` clean
- [ ] `git grep -nE 'file:/{2}|/U[s]ers/' -- docs data eval || true` (forbidden scan)

## C1: Dataset skeleton (Progress: 30%)
- [ ] Define `<dataset_id>` (e.g. `seed-mini-v0001`)
- [ ] Create `data/eval/datasets/<dataset_id>/cases.jsonl`
- [ ] Create `data/eval/datasets/<dataset_id>/dataset.meta.json`
- [ ] Ensure fields match EVAL_SPEC (case_id, query, expectation, tags)

## C2: Run artifacts writer (Progress: 60%)
- [ ] Implement `run_id` generation (`run__YYYYMMDD...`) in `eval/run_eval.py`
- [ ] Create `.local/rag_eval/runs/<run_id>/`
- [ ] Generate `run.meta.json` (git info, timestamps, config)
- [ ] Generate `results.jsonl` (status, failure_code)
- [ ] Generate `summary.json` (aggregation)
- [ ] (Recommended) Generate `command.txt`

## C3: Failure taxonomy wiring (Progress: 80%)
- [ ] Map internal errors to Fixed Failure Codes in `eval/run_eval.py`
- [ ] Ensure `results.jsonl` output uses valid codes
- [ ] Ensure `summary.json` aggregates by these codes

## C4: ROADMAP update
- [ ] Update `docs/ops/ROADMAP.md` S20 section

## C5: Gates (Progress: 90%)
- [ ] `go test ./...`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`

## C6: PR
- [ ] `git diff --stat`
- [ ] Commit & Push
