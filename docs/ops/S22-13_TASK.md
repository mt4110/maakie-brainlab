# S22-13_TASK: CI required checks のSOT同期（branch protection drift 根絶）v1

## 進捗
- S22-13: 1% (WIP) ※kickoffで着手

## Task（順序固定）
- [ ] 00. OBS作成（.local/obs/s22-13_*）
- [ ] 01. 現状観測：CI_REQUIRED_CHECKS.md / pr_merge_guard.sh / branch protection snapshot を OBS に保存
- [ ] 02. CI_REQUIRED_CHECKS.md に “required_checks_sot:v1” ブロックを追加（機械可読）
- [ ] 03. ops/required_checks_sot.sh を追加（gh api → contexts 抽出 → SOT比較 → OK/ERROR）
- [ ] 04. ops/pr_merge_guard.sh に drift 検知を組み込み（driftなら STOP=1）
- [ ] 05. STATUS.md を S22-13: 1% に更新（手で1行）
- [ ] 06. ローカルで ops/required_checks_sot.sh を実行し、OK を観測ログ化
- [ ] 07. CI green 確認（軽く：yaml lint / go test は必要最小）
- [ ] 08. PR作成 → checks green
- [ ] 09. merge guard 経由で merge
- [ ] 10. closeout：TASK/STATUS を 100% へ更新し main へ反映

## 失敗時（止まらない）
- ERROR: を出して STOP=1 にし、以降を SKIP（プロセス終了で制御しない）
- SKIP: 理由を1行残す（監査ログ）
