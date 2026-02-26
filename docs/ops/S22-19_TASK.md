# S22-19 TASK — Ship Automation Generalization
Last Updated: 2026-02-26

## Checklist
- [x] `ops/phase_ship.py` を追加（phase指定 ship helper）
- [x] branch 名から phase 推測ロジックを実装
- [x] guard + verify-il + optional reviewpack を組み込み
- [x] commit/push/ci-self gate/PR create-edit を実装
- [x] `Makefile` に `phase-ship` ターゲットを追加

## Result
- S22-16専用フローに依存せず、次節でも同型shipが実行可能。

