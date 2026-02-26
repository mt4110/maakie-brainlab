# S23-08 PLAN — Partial Checkpoint Artifacts for Thread Runner
Last Updated: 2026-02-26

## Goal
- runner 実行中にケース単位で partial 成果物を出力し、途中中断時でも進捗が失われないようにする。

## Why Now
- timeout/retry で耐停止性は上がったが、プロセス異常終了時に最終 `cases.jsonl` が残らないリスクがある。
- ケースごとに中間保存すれば、途中停止時の診断と再開判断が容易になる。

## Acceptance Criteria
- `--out` 配下に以下を常時更新する:
  - `cases.partial.jsonl`（1ケース完了ごとにappend）
  - `summary.partial.json`（1ケース完了ごとにoverwrite）
- 最終成果物（`cases.jsonl`, `summary.json`）は従来通り出力する。
- partial 書き込み失敗時も stopless で次ケースへ継続し、`ERROR` ログに記録する。
- partial artifact の存在と件数一致をテストで検証する。

## Impacted Files
- `docs/ops/S23-08_PLAN.md` (new)
- `docs/ops/S23-08_TASK.md` (new)
- `scripts/il_thread_runner_v2.py`
- `tests/test_il_thread_runner_v2.py`

## Design (v1)
- per-case end で:
  - `cases.partial.jsonl` に record を追記
  - 現在までの records で `summary.partial.json` を再計算
- final では:
  - `cases.jsonl` / `summary.json` を確定書き込み

## Non-Goals
- 自動resume機能
- partialファイルのローテーション
