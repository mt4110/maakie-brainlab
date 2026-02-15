# S17-03: Run Always 1h (scheduled) Failure — Plan (SOT-driven)

## SOT (唯一の基準)

*   **Workflow**: `.github/workflows/run_always_1h.yml`
*   **Failure Type**: scheduled run on main
*   **Failed Run**:
    *   **Run ID**: 22027626252
    *   **URL**: https://github.com/mt4110/maakie-brainlab/actions/runs/22027626252
    *   **event**: schedule
    *   **conclusion**: failure
    *   **failed step**: run-always-1h (Script)
    *   **timestamp**: 2026-02-15T01:36:34Z

## Evidence directory

`docs/evidence/s17-03/`

## Goal

*   `run_always_1h` が main の schedule で安定して PASS する
*   落ちたら「原因が一発で分かるログ」になる

## Non-Goals

*   evalロジック拡張
*   大規模リファクタ
*   “とりあえずリトライ” で真因を隠す

## Proposed Changes

### Configuration / Scripts

#### [MODIFY] [reviewpack_policy.toml](ops/reviewpack_policy.toml)
*   Check if `require_signature_in_ci = true` is intended for this automated run. If so, ensure keys are passed correctly.

#### [MODIFY] [run_always_1h.sh](ops/run_always_1h.sh)
*   Harden diagnostics to print environment variables related to signing (S6_SIGNING_KEY, etc.)
*   Ensure commands that require signing (like `reviewpack submit` and `evidencepack pack`) are called with the correct flags if the environment variable is present.

## Verification Plan

### Automated Tests
*   `bash ops/run_always_1h.sh` locally (with and without `REVIEWPACK_POLICY_MODE=ci`)
*   `make test`

### Manual Verification
*   Verify `docs/evidence/s17-03/` contains the failed evidence and the fix evidence.
