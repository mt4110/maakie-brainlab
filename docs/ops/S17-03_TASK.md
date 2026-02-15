# TASK: S17-03 Stabilization of run_always_1h
Status: DONE
Owner: ambi
Progress: 100%

## 0) Safety Snapshot（0%→10%）
- [x] repo_root := `cd "$(git rev-parse --show-toplevel)"`
- [x] 現在ブランチ確認（`s17-03-run-always-1h-fix-v1`）
- [x] git status -sb（clean 確認済み）
- [x] 必要コマンド存在確認（git/go/shasum 確認済み）

## 1) 探索（Paths / Branch / Files）(10%→25%)
- [x] docs_home を探索して確定（`docs/ops`）
- [x] 対象Plan/Taskの実ファイルパスを探索して確定
- [x] 失敗RUNログ (`22027626252`) の回収と保存（`docs/evidence/s17-03/`）

## 2) 実装（25%→60%）
- [x] `submit.go`: `--sign-key` フラグ追加と署名呼び出し関数修正
- [x] `run_always_1h.sh`: 署名パス・自動鍵生成ロジックの追加
- [x] `.gitignore`: `.tmp/` 除外設定追加
- [x] 余計な差分が無いか diff を確認（`git diff main --stat` で確認済み）

## 3) Gate（60%→85%）
- [x] `make test` (PASS)
- [x] `bash ops/run_always_1h.sh` (100% PASS)
- [x] 生成物 SHA256 を記録 (Ritual Calculation)
  - [x] review_bundle_20260215_121251.tar.gz
  - [x] SHA256: `03cc0575170393c7481c96452d9a0aae5feef7480901993c71ab7b0a89416fff`

## 4) 仕上げ（85%→100%）
- [x] commit (規約遵守)
- [x] push (HEAD)
- [x] PR 更新 (#51 本文へ Ritual 追加)
- [x] DONE: `docs/evidence/s17-03/fix_evidence.txt` を確定証拠として保存

## Evidence（証拠）
- **Last Golden Run**: `2026-02-15 12:12:51 (local)`
- **Bundle**: `review_bundle_20260215_121251.tar.gz`
- **Bundle SHA256**: `03cc0575170393c7481c96452d9a0aae5feef7480901993c71ab7b0a89416fff`
- **Success Run**: `log_pass_22028710788.txt`
- **Log**: [fix_evidence.txt](../evidence/s17-03/fix_evidence.txt)
