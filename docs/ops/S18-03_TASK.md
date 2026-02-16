# S18-03 TASK

1. ファイル作成/更新
- .github/pull_request_template.md
- .github/workflows/pr_body_required.yml
- docs/ops/S18-03_PLAN.md / S18-03_TASK.md

2. S18_PLAN / S18_TASK に S18-03 を追記（分母更新）

3. ゲート実行
- make test
- go run cmd/reviewpack/main.go submit --mode verify-only

4. PR作成（このPR自身が marker で落ちないよう本文から除去）
