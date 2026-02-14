# S15-09 PLAN (S15-09/10 - 1PR)

## Goal

- S15-09 を完了する（同一PRで S15-10 まで到達する前提）
- SUBMIT コマンドの堅牢化（Part A: Submission Hardening）

## Scope

- `internal/reviewpack/submit.go`, `internal/reviewpack/pack.go`
- 変更対象:
  - `findLatestEvalResult` の改善（最新の有効な評価結果を確実に選択する）
  - `runPreflightChecks` に doc link guard (file://) の動的な文字列チェックを追加

- 非対象:
  - VERIFY コマンドの実装変更（S15-10で実施）

## Inputs (Source of Truth)

- docs/ops/S15_07_10_DEPENDENCY_MATRIX.md
- docs/ops/IF_FAIL_C10FIX04.md (file:// guard context)
- docs/ops/IF_FAIL_S7.md (verify-only failure context)

## Pseudocode (IF/ELSE/FOR/STOP)

- IF current_branch != "s15-09-10-fixpack-v1": ERROR → STOP
- IF working_tree_dirty: ERROR → STOP

- FOR each candidate in [internal/reviewpack/submit.go]:
  - IF !findLatestEvalResult logic exists:
    - SKIP: logic not found in this file
    - CONTINUE
  - apply logic hardening (Sort by timestamp, validate readability)
  - BREAK

- IF scope expands unexpectedly: ERROR → STOP

## Risks

- 決定論を壊す要素（時刻/順序/OS依存）が入り込む
- 既存Gateに影響

## Exit Criteria

- make test PASS
- reviewpack submit --mode verify-only PASS
- Evidence が Task.md に残る
