# S20-02 Task — RAG eval wall v1

## Progress
- 0% Start
- 10% Plan/Task fixed
- 40% EVAL_SPEC: dataset fixed
- 70% EVAL_SPEC: run artifacts fixed
- 85% EVAL_SPEC: failure taxonomy fixed
- 90% Gates pass
- 100% PR merged

## C0: Safety Snapshot
- [ ] `git status -sb` clean
- [ ] `git grep -nE 'file:/{2}|/U[s]ers/' -- docs/ops || true`

## C1: Dataset spec (fixed inputs)
- [ ] dataset の置き場所を EVAL_SPEC に確定
- [ ] dataset フォーマット（必須フィールド/任意フィールド）を EVAL_SPEC に確定
- [ ] IDルール（不変性・追加時のルール）を EVAL_SPEC に確定

## C2: Run artifacts spec (fixed outputs)
- [ ] 実行出力の保存先・命名規則を EVAL_SPEC に確定
- [ ] 人間可読＋機械可読の最小セットを EVAL_SPEC に確定
- [ ] 比較（前回runとの差分）に必要なキーを EVAL_SPEC に確定

## C3: Failure taxonomy spec (fixed labels)
- [ ] 失敗分類の一覧と意味を EVAL_SPEC に確定（名称は凍結）
- [ ] “分類の付け方（判定観点）”を短く固定

## C4: ROADMAP update
- [ ] `docs/ops/ROADMAP.md` の S20 セクションに S20-02 を追記

## C5: Gates
- [ ] `go test ./...`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`

## C6: PR
- [ ] `git push -u origin HEAD`
- [ ] PR作成（`./ops/pr_create.sh` or `gh pr create --fill`）
- [ ] CI green → merge
