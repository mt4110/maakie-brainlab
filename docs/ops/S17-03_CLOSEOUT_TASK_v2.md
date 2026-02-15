# S17-03 Closeout Task v2 (Checklist)

## 0) Preflight
- [ ] `git status -sb` (Check: clean)

## 1) Hygiene Capsule (NO forbidden token in tracked files)
- [ ] `bash ops/finalize_clean.sh --check` (Check: PASS)
- [ ] FAIL の場合:
  - [ ] `bash ops/finalize_clean.sh --fix`
  - [ ] `git add -u -- docs ops .github internal .githooks`
  - [ ] `bash ops/finalize_clean.sh --check` (Check: PASS)

## 2) Canonical Capsule
- [ ] tracked docs は PR body の Canonical Ritual を参照している (Check)
- [ ] tracked docs に canonical tuple（commit/bundle/sha の固定値）が直書きされていない (Check)

## 3) Gates
- [x] `make test` (PASS)
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only` (PASS)

## 4) Commit Hardened Capsule
- [ ] `git add -- docs ops .github internal .githooks`
- [ ] `git commit -m "fix(hooks): harden pre-commit hygiene capsule (fail-closed + scope-only staging)"`
- [ ] `git push`

## 5) PR Body Update (Human Action)
- [ ] PR #51 の Canonical Ritual を「現在のHEAD + そのHEADでのverify-only 1回分」に更新
- [ ] NOTE: 新コミットが無いのに bundle 名/sha が変わっても Canonical を更新しない（Observation 扱い）

## 6) Final
- [ ] `make test` (PASS)
- [ ] verify-only (PASS)
- [ ] merge
