# S22-17 TASK — pr_merge_guard Contract Fix
Last Updated: 2026-02-26

## Checklist
- [x] merge guard の現行契約差分を洗い出し（実装 vs docs）
- [x] milestone 系を non-blocking に変更
- [x] merge 実行を merge-commit に固定
- [x] `--match-head-commit` で head SHA pin を追加
- [x] PR workflow ドキュメントに契約を反映

## Result
- milestone 状態は merge 停止条件から除外し、required checks/check-runs を停止条件として維持。
- merge 手順を運用規約どおり merge-commit に統一。

