# S21-03 TASK

## Preflight (落ちない)
- [ ] repo検出（OK/ERROR）
- [ ] `git status -sb` を表示（dirtyなら人間判断で中断）

## Locate (実パス確定: for/continue/break)
- [ ] milestone_required workflow 実在確認（FOUND_REQ を固定）
- [ ] (if exists) milestone_advisory workflow 実在確認（FOUND_ADV を固定、なければSKIP理由1行）

## Update (Workflow)
- [ ] `$FOUND_REQ` の `on.pull_request.types` を固定列挙に変更
  - opened / reopened / synchronize / edited / labeled / unlabeled / milestoned / demilestoned
- [ ] `$FOUND_REQ` の判定ロジックを API による「現在PR取得」へ変更
  - payload依存 (`github.event.pull_request.milestone`) を排除
- [ ] (if exists) `$FOUND_ADV` も同様に types と判定方式を揃える

## Update (Docs)
- [ ] docs/ops/PR_WORKFLOW.md に rerun罠/真実取得（API）原則を追記
- [ ] docs/ops/STATUS.md に S21-03 行を追加（0% / Kickoff / Last Updated更新）
- [ ] docs/ops/S21-03_PLAN.md を作成
- [ ] docs/ops/S21-03_TASK.md を作成

## Verify (軽量)
- [ ] `git diff --name-only origin/main...HEAD` で差分範囲確認（workflow + docsのみ）
- [ ] `rg -n "milestoned|demilestoned" "$FOUND_REQ"` で types が入ったことを確認
- [ ] `rg -n "github-script@|pulls.get|api.github.com" "$FOUND_REQ"` で API 真実取得が入ったことを確認

## Verify (挙動: PR上で確認)
- [ ] このPRで Milestone未設定の状態を作り、milestone_required が FAIL になることを確認
- [ ] PRにMilestoneを後付け → `milestoned` で自動再判定が走り PASS になることを確認（rerun不要）
- [ ] Milestoneを外す → `demilestoned` で自動再判定が走り FAIL になることを確認

## Verify (重い/任意: 最後に1回だけ)
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`（任意）
