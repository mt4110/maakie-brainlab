# S7 Plan: Run Always & Strict Eval Isolation

## Core Philosophy
1.  **CI = Verify-Only**: CI never runs evaluation (`make run-eval`). It strictly verifies the pack structure and reuses `latest.jsonl`.
2.  **Eval = Strict (Isolated)**: Strict evaluation runs on self-hosted runners via `eval_strict.yml` (Nightly/Dispatch).
3.  **Run Always**: CI artifacts are uploaded check-or-fail.

## Triage
See `docs/ops/IF_FAIL_S7.md`.
## Triage
See `docs/ops/IF_FAIL_S7.md`.

## Verify-Only Seeding
- **CI**: Uses `make seed-eval` (copies `eval/fixtures/latest.jsonl` -> `eval/results/ci.jsonl`) to simulate a previous result.
- **Local Dev**: Use `make seed-eval` to simulate CI state for fast iteration.
