# S18-03 PLAN

目的
- PR作成時にテンプレが自動で入る状態を保証する
- CIで『空』だけでなく『テンプレ未編集』も確実にブロックする

スコープ
- .github/pull_request_template.md を sentinel 付きで確定
- .github/workflows/pr_body_required.yml を sentinel 判定付きに強化
- docs/ops の S18 記録更新（S18-03 追加）

受け入れ条件（Acceptance）
- PR本文が空のとき workflow が FAIL する
- PR本文に PR_BODY_TEMPLATE_v1 が含まれると workflow が FAIL する
- PR本文から marker を消して内容を埋めると PASS する

ゲート（Gates）
- make test: PASS
- reviewpack submit --mode verify-only: PASS
