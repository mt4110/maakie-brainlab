# S15-10 PLAN (S15-09/10 - 1PR)

## Goal

- S15-10 を完了する（このPRで S15-09/10 を close）
- VERIFY コマンドの緊密化（Part B: Verification Hardening）

## Scope

- `internal/reviewpack/verify.go`, `internal/reviewpack/evidence.go`, `internal/reviewpack/utils.go`
- 変更対象:
  - `runVerify` に `10_git_log.txt` / `30_make_test.log` / `40_self_verify.log` の存在チェックを追加
  - rawログおよび `30_make_test.log` は同名 `.sha256` サイドカーを必須とする（10/11/40）
  - Evidence marker の判定条件を厳格化（全ての必須ログが PASS していることを確認）

## Inputs (Source of Truth)

- docs/ops/S15_07_10_DEPENDENCY_MATRIX.md
- docs/ops/IF_FAIL_S7.md (Verification failure contexts)

## Pseudocode

- IF S15-09 gate 未達: ERROR → STOP（順序を守る）

- FOR each log in [10_git_log.txt, 30_make_test.log, 40_self_verify.log]:
  - IF log missing in logs/raw/:
    - ERROR: missing mandatory evidence log → STOP
  - ELSE:
    - validate content (ensure no fatal markers)
    - CONTINUE

- IF introduces non-determinism: ERROR → STOP

## Exit Criteria

- make test PASS
- reviewpack submit --mode verify-only PASS
- Evidence が残る
