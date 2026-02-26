# S23-10 PLAN — Thread Runner v2 Suite Closeout
Last Updated: 2026-02-26

## Goal
- Thread Runner v2 の主要検査（smoke/replay/doctor）を1コマンドで実行できる closeout スイートを完成させる。

## Why Now
- S23-04〜09 で機能は揃ったが、運用チェックが分散している。
- S23スレッドを締める前に、再現可能な統合チェック導線を固定する。

## Acceptance Criteria
- `scripts/il_thread_runner_v2_suite.py` を追加し、以下を順次実行:
  - thread runner validate-only run
  - artifact doctor
  - replay check
  - thread smoke
- 各ステップ結果を `suite.summary.json` に保存する。
- Makefile に `verify-il-thread-v2` ターゲットを追加する。
- `verify-il` から `verify-il-thread-v2` を呼び出せる。
- suite の正常系テストを追加する。

## Impacted Files
- `docs/ops/S23-10_PLAN.md` (new)
- `docs/ops/S23-10_TASK.md` (new)
- `scripts/il_thread_runner_v2_suite.py` (new)
- `tests/test_il_thread_runner_v2_suite.py` (new)
- `Makefile`

## Non-Goals
- PR 作成
- 重量級 eval wall 実行
