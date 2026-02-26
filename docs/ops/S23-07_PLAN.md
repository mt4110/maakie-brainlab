# S23-07 PLAN — Entry Retry Policy for Thread Runner
Last Updated: 2026-02-26

## Goal
- `il_thread_runner_v2` の `entry` 一時失敗をケース内リトライで吸収し、全体停止リスクをさらに下げる。

## Why Now
- S23-05 で timeout制御は入ったが、短時間の一時失敗（初回のみ失敗）は即 `ERROR` になる。
- 「止まるのが最悪」を避けるため、限定的な retry で成功率を底上げする。

## Acceptance Criteria
- `--entry-retries <int>` を追加（default=0）。
- `entry` 失敗時、`entry_retries` 回まで再試行する。
- 成功時は `entry_status=OK`、失敗時は `entry_status=ERROR`。
- case record に `entry_attempts` を記録する。
- retry 成功ケース / retry 枯渇ケースのユニットテストを追加する。

## Impacted Files
- `docs/ops/S23-07_PLAN.md` (new)
- `docs/ops/S23-07_TASK.md` (new)
- `scripts/il_thread_runner_v2.py`
- `tests/test_il_thread_runner_v2.py`

## Design (v1)
- total attempts = `1 + entry_retries`
- 各attemptで `entry.stdout.log` / `entry.stderr.log` を更新し、履歴は `entry.stdout.attemptNN.log` も残す。
- retry条件:
  - timeout / returncodeエラー / protocol不一致 / artifact不足
- retryしない条件:
  - mode=validate-only
  - compile失敗（fail-closed）

## Non-Goals
- 無制限リトライ
- exponential backoff 実装
- compile 側リトライ
