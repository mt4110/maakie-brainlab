# S21-03 TASK

## Preflight (落ちない)
- [x] repo検出（OK/ERROR）
- [x] `git status -sb` を表示（dirtyなら人間判断で中断）

## Locate (実パス確定: for/continue/break)
- [x] milestone_required workflow 実在確認（FOUND_REQ を固定）
- [x] (if exists) milestone_advisory workflow 実在確認（FOUND_ADV を固定、なければSKIP理由1行）

## Update (Workflow)
- [x] `$FOUND_REQ` の `on.pull_request.types` を固定列挙に変更
  - opened / reopened / synchronize / edited / labeled / unlabeled / milestoned / demilestoned
- [x] `$FOUND_REQ` の判定ロジックを API による「現在PR取得」へ変更
  - payload依存 (`github.event.pull_request.milestone`) を排除
- [x] (if exists) `$FOUND_ADV` も同様に types と判定方式を揃える

## Update (Docs)
- [x] docs/ops/PR_WORKFLOW.md に rerun罠/真実取得（API）原則を追記
- [x] docs/ops/STATUS.md に S21-03 行を追加（0% / Kickoff / Last Updated更新）
- [x] docs/ops/S21-03_PLAN.md を作成
- [x] docs/ops/S21-03_TASK.md を作成

## Verify (軽量)
- [x] `git diff --name-only origin/main...HEAD` で差分範囲確認（workflow + docsのみ）
- [x] `rg -n "milestoned|demilestoned" "$FOUND_REQ"` で types が入ったことを確認
- [x] `rg -n "github-script@|pulls.get|api.github.com" "$FOUND_REQ"` で API 真実取得が入ったことを確認

## Verify (挙動: PR上で確認)
- [x] このPRで Milestone未設定の状態を作り、milestone_required が FAIL になることを確認
- [x] PRにMilestoneを後付け → `milestoned` で自動再判定が走り PASS になることを確認（rerun不要）
- [x] Milestoneを外す → `demilestoned` で自動再判定が走り FAIL になることを確認

## Verify (重い/任意: 最後に1回だけ)
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`（任意）
