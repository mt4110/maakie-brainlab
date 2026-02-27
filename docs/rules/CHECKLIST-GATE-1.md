# S4.4 Gate-1 Checklist (verify-only)

## Context
This checklist is for verifying the implementation of S7-20 (Unified Submit Logic).

## Verification Steps

- [x] Run `make test` locally to ensure no regressions.
- [x] Run `go run cmd/reviewpack/main.go submit --mode verify-only` locally.
- [x] Verify that `31_make_run_eval.log` indicates SKIP and records reason/sha.
- [x] Verify that `00_meta.txt` contains `eval_source_path` and `eval_result_sha`.

## Pre-PR / Pre-Merge Check
- [x] **Run Gate-1**: `make gate1` must PASS.
- [x] **Scope Check**: No changes to `data/`, `index/`, `logs/`, `models/` structure (symlinks respected).
- [x] **Eval Verification**:
    - [x] `passed=True` for all relevant questions.
    - [x] `details.has_sources=True` (or equivalent citation) is present for all answered questions (Exception: `negative_control` types).
- [x] **Determinism**: Re-running yields consistent results under the same conditions; if drift occurs, record the cause (model parameters / external changes).

## Troubleshooting Gate-1 Failure
1. **Did `pytest` fail?**
    - Check unit test logs (`make test`). Fix strict logic bugs first.
2. **Did `eval` fail?**
    - Check `passed=False`: Model gave wrong answer.
    - Check `passed=True` but `gate1` failed: Model gave right answer **without details.has_sources=True** (Hallucination/Lucky Guess).
    - Check `latency`: Is the model responding?
3. **Did `symlinks` fail? (external links check)**
    - Run `ls -l data index logs models` to verify symlinks are active to external storage.
