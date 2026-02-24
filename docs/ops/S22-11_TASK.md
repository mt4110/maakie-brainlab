# S22-11_TASK: Milestone "意識ゼロ化" (zero-thought) v1

## 進捗

- S22-11: 1% (WIP) ※kickoffで着手

## Task（順序固定）

- [x] 00. OBSディレクトリ作成（.local/obs/s22-11\_\*）
- [x] 01. 現状観測：milestone関連のworkflow/設定を rg で局所探索
- [x] 02. 新規workflow追加：.github/workflows/s22\_milestone\_autofill.yml を作成
- [x] 03. merge guard強化：ops/pr\_merge\_guard.sh に "milestone未設定なら自動付与→再検査" を追加
- [x] 04. SOT更新：docs/ops/STATUS.md に S22-11 行を追加/更新（1% WIP）
- [ ] 05. 軽量検証：変更ファイルの最小チェック
- [ ] 06. PR作成（milestoneは付けない）：タイトル/本文（SOT/証拠スタイル）で提出
- [ ] 07. 実地検証：PR上で milestone が自動付与されることを観測ログ化
- [ ] 08. merge前検証：merge guard が milestone 無しでも自己修復できることを観測
- [ ] 09. closeout：PLAN/TASK/STATUS を 100% にして 1PRで閉じる

## 失敗時ルール（止まらない）

- ERROR: を出して STOP=1 にし、以降ステップを SKIP する（プロセスは継続）
- SKIP: 理由を1行で必ず残す（監査ログ）
