# S22-14_TASK: IL入口の単一化（P0）+ 常時検証 v1

## 進捗
- S22-14: 100% ✅

## Task（順序固定 / stopless）
- [x] 00. OBS作成（.local/obs/s22-14_*）
- [x] 01. 現状観測：入口候補探索（rg --threads 2）→ OBS保存
- [x] 02. 入口候補の一覧を抽出（ファイルパスのユニーク化）→ OBS保存
- [x] 03. Canonical Entrypoint を 1つ確定（docsに反映：CANONICAL_ENTRYPOINT_TBD を置換）
- [x] 04. 旧入口を canonical へ委譲（wrapper化）or 明示禁止
- [x] 05. repo内参照（Makefile/ops/workflow/docs/ops）を canonical に寄せる
- [x] 06. 常時検証（guard）追加：canonical以外の参照を検知し ERROR を出す（exitしない）
- [x] 07. STATUS.md を S22-14: 1% (WIP) 維持（無ければ挿入）
- [x] 08. ローカル軽量検証（guard実行 / diff stat / entry --help 等）
- [x] 09. PR作成 → checks green（重いテストは回さない）
- [x] 10. merge guard 経由で merge
- [x] 11. closeout：TASK/STATUS を 100% ✅へ

## 失敗時（止まらない）
- ERROR: を出して STOP=1、以降は SKIP（終了コードに依存しない）
- SKIP: 理由を必ず1行残す（監査ログ）
