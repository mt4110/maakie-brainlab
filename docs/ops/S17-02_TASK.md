# TASK: S17-02 IL validator / canonicalizer (Contract v1) [HARDCORE+]
Status: DONE
Owner: ambi
Progress: 100%

## 0) Safety Snapshot（0%→10%）
- [x] repo_root を取得（`/Users/takemuramasaki/dev/maakie-brainlab`）
- [x] 現在ブランチ確認（merged to `main`）
- [x] git status -sb（clean 確認済み）
- [x] 必要コマンド存在確認（git/go/python 確認済み）

## 1) 探索（Paths / Branch / Files）(10%→25%)
- [x] docs_home を探索して確定（`docs/ops`）
- [x] 対象Plan/Taskの実ファイルパスを探索して確定
- [x] Contract SOT (`docs/il/IL_CONTRACT_v1.md`) の実在確認

## 2) 実装（25%→60%）
- [x] `il_validator.py`: 予約語 `errors` の全面禁止ロジック実装
- [x] `il_validator.py`: int 厳密評価 (no bool/float) と 53-bit 範囲チェック実装
- [x] `normalize.py`: `sys.path` 契約の `src` 固定化
- [x] `Makefile`: `PYENV` の `PYTHONPATH` 契約修正

## 3) Gate（60%→85%）
- [x] `make test` (PASS)
- [x] `verify-only` (PASS)
- [x] 生成物 SHA256 を記録 (Ritual Calculation)
  - [x] `review_bundle_20260215_102147.tar.gz`
  - [x] SHA256: `bc9bd32aa84863fb61ebd5114169804f26018977825e4cff715aab1002c17aee`

## 4) 仕上げ（85%→100%）
- [x] commit (規約遵守)
- [x] push (HEAD)
- [x] PR 作成 (#50)
- [x] DONE: `docs/ops/S17-02_PLAN.md` への事後記録
