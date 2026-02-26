# S23-06 PLAN — Thread Runner Replay Determinism Gate
Last Updated: 2026-02-26

## Goal
- `il_thread_runner_v2` を同一入力で2回実行したときの再現性（`cases.jsonl` sha一致）を自動検証する。

## Why Now
- S23-05 で耐停止性は強化できたが、運用では「止まらない」だけでなく「毎回同じ出力」が必要。
- `V2` 系の契約に合わせ、軽量 replay gate を常用できる形にする。

## Acceptance Criteria
- `scripts/il_thread_runner_v2_replay_check.py` を追加し、同一ケースを2回実行して比較できる。
- レポート `il.thread.replay.report.json` に run1/run2 の `cases.jsonl` sha と一致判定を出力する。
- mismatch 時も stopless で report を残し、`ERROR:` ログで明示する。
- `tests/test_il_thread_runner_v2_replay.py` を追加し、正常系（一致）を回帰防止する。

## Impacted Files
- `docs/ops/S23-06_PLAN.md` (new)
- `docs/ops/S23-06_TASK.md` (new)
- `scripts/il_thread_runner_v2_replay_check.py` (new)
- `tests/fixtures/il_thread_runner/cases_smoke.jsonl` (new)
- `tests/test_il_thread_runner_v2_replay.py` (new)

## Design (v1)
- replay check:
  - run1: `il_thread_runner_v2 --mode validate-only`
  - run2: 同一設定で再実行
  - compare: `run1/cases.jsonl` vs `run2/cases.jsonl` sha256
- report schema:
  - `schema=IL_THREAD_REPLAY_CHECK_v1`
  - `status=OK|ERROR`
  - `mode`
  - `run1_sha256_cases_jsonl`
  - `run2_sha256_cases_jsonl`
  - `match` (bool)

## Non-Goals
- runモードの重量級再現性検証（このフェーズは validate-only を標準）
- PR gate への必須化
