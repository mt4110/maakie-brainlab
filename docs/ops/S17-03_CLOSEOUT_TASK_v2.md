# S17-03 Closeout Task v2 (Checklist)

## 0) Preflight
- [ ] `git status -sb` (Check: clean)

## 1) Hygiene Capsule (NO forbidden token in tracked files)
- [ ] `bash ops/finalize_clean.sh --check` (Check: PASS)
- [ ] FAIL の場合:
  - [ ] `bash ops/finalize_clean.sh --fix`
  - [ ] `git add -u -- docs ops .github internal .githooks`
  - [ ] `bash ops/finalize_clean.sh --check` (Check: PASS)

## Rebase/Merge Safety
- merge / rebase / cherry-pick / revert などの **敏感操作中はガードをスキップ（exit 0）**します。
  - 理由: 競合解消フローに介入して “止める/書き換える” のが一番危険だから。
  - ふだんの通常 commit では従来どおり **check→fix→check** の自動化が動きます。

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

## Pre-commit が止めたときの復旧（Fail Closed）
※ このカプセルは「混ざった状態」を許さない設計です。落ち着いて順番にほどく。

- **スコープ内（docs/ ops/ .github/ internal/ .githooks）に未ステージ変更がある**  
  → `git add -u -- docs ops .github internal .githooks` で揃えるか、`git stash -u` で退避。

- **スコープ外に未ステージ変更がある**  
  → 先に `git add -u -- :/` で全部ステージするか、`git stash -u` で退避。  
  （※カプセルはワークツリー安定性を優先して止まります）

- **Fix がスコープ外を触って止まった**  
  → いったん `git status -sb` で汚れを確認 → 必要なら `git restore --worktree -- :/` で戻す。  
  その後 `bash ops/finalize_clean.sh --fix` を単独実行して、どこを触ったかを観察してから方針を決める。
