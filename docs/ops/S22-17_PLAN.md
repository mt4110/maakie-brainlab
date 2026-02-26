# S22-17 PLAN — pr_merge_guard Contract Fix
Last Updated: 2026-02-26

## Goal
- `ops/pr_merge_guard.sh` の契約を明文化し、実装と運用ドキュメントを一致させる。

## Acceptance Criteria
- milestone 系の観測/補正は non-blocking として扱う。
- required checks gate と check-runs gate は blocking のまま維持する。
- merge 実行方式を merge-commit に固定する。
- dry-run と merge 実行ログで契約が読み取れる。

## Impacted Files
- `ops/pr_merge_guard.sh`
- `docs/ops/PR_WORKFLOW.md`
- `docs/ops/S22-17_PLAN.md`
- `docs/ops/S22-17_TASK.md`

## Design
- milestone 欠落時は autofix を試行し、失敗は WARN（STOPにしない）。
- `milestone_required` status/check-run は観測のみ（WARN可能、STOPにしない）。
- 実 merge は `gh pr merge --merge --match-head-commit <sha>` を使用する。

