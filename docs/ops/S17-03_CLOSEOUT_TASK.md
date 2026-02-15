# TASK: S17-03 Closeout (Final)

## 0) Snapshot
- [ ] `cd "$(git rev-parse --show-toplevel)"`
- [ ] `git rev-parse --abbrev-ref HEAD` (Check: != main)
- [ ] `git status -sb` (Check: clean)

## 1) Hygiene
- [ ] `rg -n "file:/{2}" docs ops .github internal` (Check: 0 hits)
- [ ] hits>0 の場合：該当箇所を `[FILE_URI]` or `file:/{2}` に置換 → 再チェック

## 2) Canonical leakage check
- [ ] `rg -n "0310890|review_bundle_20260215_135256|7f444f" docs ops .github internal`
    - Check: 0 hits (Old canonical must be gone)
- [ ] `rg -n "86751b4|review_bundle_20260215_144855|7d9d7d11" docs ops .github internal`
    - Check: 0 hits (New canonical must NOT be in repo)

## 3) PR body update (Human)
- [ ] PR #51 本文の Canonical Ritual を 最終値に差し替え
- [ ] NOTE で「以後は Observation、Canonical 更新しない」を明記

## 4) Gates
- [ ] `make test` (PASS)
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only` (PASS)
- [ ] `git status -sb` (clean)

## 5) Finish
- [ ] Status: DONE / Progress: 100%
- [ ] Merge
