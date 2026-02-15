# S17-03 Closeout Task v2 (Checklist)

## 0) Preflight
- [ ] `git status -sb` (Check: clean)

## 1) Hygiene Capsule (NO forbidden token in tracked files)
- [ ] `FORBID="$(printf '%s%s' 'file' '://')"`
- [ ] `rg -n "$FORBID" docs ops .github internal .githooks` (Check: 0 hits)
- [ ] hits > 0 の場合:
  - [ ] `bash ops/finalize_clean.sh --fix`
  - [ ] `git add -- docs ops .github internal .githooks`
  - [ ] `rg -n "$FORBID" docs ops .github internal .githooks` (Check: 0 hits)

## 2) Canonical Capsule
- [ ] tracked docs は PR body の Canonical Ritual を参照している (Check)
- [ ] tracked docs に canonical tuple（commit/bundle/sha の固定値）が直書きされていない (Check)

## 3) Gates
- [x] `make test` (PASS)
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only` (PASS)

## 4) Commit Hardened Capsule
- [ ] `git add -- docs ops .github internal .githooks`
- [ ] `git commit -m "fix(hooks): harden pre-commit hygiene capsule (scope-only staging)"`
- [ ] `git push`

## 4) PR Body Update (Human Action)
- [ ] PR #51 の Canonical Ritual を「現在のHEAD + そのHEADでのverify-only 1回分」に更新
- [ ] NOTE: 新コミットが無いのに bundle 名/sha が変わっても Canonical を更新しない（Observation 扱い）

## 5) Final
- [ ] `make test` (PASS)
- [ ] verify-only (PASS)
- [ ] merge
