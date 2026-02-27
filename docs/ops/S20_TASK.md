# S20 Task — Ops Roadmap Index v1 (docs/ops 総合目次)

## Progress
- 0% Start
- 10% Branch + skeleton exists
- 40% ROADMAP generated
- 70% S19 docs de-templated
- 90% Gates pass
- 100% PR merged (+ optional main re-run)

## C0: Safety Snapshot
- [x] `git status -sb` clean

## C1: Add ROADMAP入口
- [x] `docs/ops/ROADMAP.md` を追加（入口・凡例・シリーズ俯瞰）

## C2: S15〜S19 view (正直ステータス)
- [x] ROADMAP のシリーズ俯瞰を手で補強（完了/進行中/迷子ポイント）
  - まずは S19 を確実に埋める（他はTBDでもOK）

## C3: Fix the “迷子の根” (S19 docs)
- [x] `docs/ops/S19_PLAN.md` をテンプレ→実態に更新
- [x] `docs/ops/S19_TASK.md` をテンプレ→実態に更新
- [x] S19-02 merged / main gate PASS を明記

## C4: Gates
- [x] `go test ./...`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`

## C5: PR
- [x] `git push -u origin HEAD`
- [x] PR作成（`./ops/pr_create.sh` か `gh pr create --fill`）
- [x] CI green
