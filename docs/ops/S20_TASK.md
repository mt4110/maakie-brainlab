# S20 Task — Ops Roadmap Index v1 (docs/ops 総合目次)

## Progress
- 0% Start
- 25% ROADMAP added
- 50% S15–S19 index wired
- 75% S19 docs de-templated
- 90% Gates pass
- 100% PR merged (+ optional main re-run)

---

## C0: Safety Snapshot (必須)
- [ ] `git status -sb` が clean
- [ ] `rg -n "file://|/Users/" docs/ops || true`（混入チェック）

---

## C1: Add ROADMAP入口
- [ ] `docs/ops/ROADMAP.md` を追加（入口・凡例・S15〜S20リンク）
- [ ] ROADMAP 最上段に「何を見ればいいか」を固定

Commit:
- `docs(ops): add ROADMAP entrypoint`

---

## C2: Wire S15〜S19 view (正直ステータス)
- [ ] S15〜S19 をリンク付きで並べる
- [ ] 完了/進行中/テンプレ残骸あり を明記

Commit:
- `docs(ops): index S15-S19 in ROADMAP`

---

## C3: Fix the “迷子の根” (S19 docs)
- [ ] `docs/ops/S19_PLAN.md` をテンプレ→実態に更新
- [ ] `docs/ops/S19_TASK.md` をテンプレ→実態に更新
- [ ] S19-02 merged / main gate PASS を明記

Commit:
- `docs(ops): fill S19 plan/task to match reality`

---

## C4: Gates (健康診断)
- [ ] `go test ./...`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`

---

## C5: PR
- [ ] `git push -u origin HEAD`
- [ ] `gh pr create --fill`
- [ ] CI green 確認
- [ ] merge 後、必要なら main で再実行：
  - `go test ./...`
  - `go run cmd/reviewpack/main.go submit --mode verify-only`

Done:
- [ ] ROADMAP が入口として機能し、迷子が再発しない状態になった

