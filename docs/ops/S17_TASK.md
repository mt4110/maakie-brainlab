# S17 TASK（00→03固定）

## Safety Snapshot（必須）
- [x] `cd "$(git rev-parse --show-toplevel)"; git status -sb`
- [x] `git rev-parse --abbrev-ref HEAD`
- [x] `git log -1 --oneline --decorate`

## S17-00 Kickoff
- [x] `docs/ops/S17_PLAN.md` を作成（目的/非ゴール/用語/成果物/ゲート/進捗定義）
- [x] `docs/ops/S17_TASK.md` を作成（00→03順序固定）
- [x] `docs/ops/S17-00_PLAN.md` を作成（分岐/停止条件）
- [x] `docs/ops/S17-00_TASK.md` を作成（チェック順序固定）

## S17-01 Contract Spec（設計）
- [x] `docs/ops/S17-01_PLAN.md` を作成（契約面/正規化/エラー/例/受け入れ）
- [x] `docs/ops/S17-01_TASK.md` を作成（GOOD/BAD例まで含める順序固定）
- [x] （S17-01で）`docs/il/IL_CONTRACT_v1.md` を作成
- [x] （S17-01で）`docs/il/il.schema.json` を作成
- [x] （S17-01で）`docs/il/examples/` を追加（GOOD/BAD最低1つずつ）

## Gates（clean tree 前提）
- [x] `make test`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`

## Commit / Push / PR
- [x] `git add docs/ops/S17*.md docs/ops/S17-*.md docs/il/*`
- [x] `git commit -m "chore(docs): kickoff S17 IL Contract v1 (milestones + spec skeleton)"`
- [x] `git push -u origin HEAD`
- [x] `gh pr create --base main --head "$(git rev-parse --abbrev-ref HEAD)" --fill`
