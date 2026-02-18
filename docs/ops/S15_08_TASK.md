# S15-08 TASK — Lock Dependencies + PR Slicing Rules

## 0) 前提確認（止まる勇気）
- MIGRATED: S21-MIG-S15-08-0001 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-08-0002 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-08-0003 (see docs/ops/S21_TASK.md)

## 1) 依存マトリクスの実体パス確定（推測禁止）
- MIGRATED: S21-MIG-S15-08-0004 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-08-0005 (see docs/ops/S21_TASK.md)

## 2) S15_08_PLAN の 確定
- MIGRATED: S21-MIG-S15-08-0006 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-08-0007 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-08-0008 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-08-0009 (see docs/ops/S21_TASK.md)

## 3) S15_08_TASK の 確定
- MIGRATED: S21-MIG-S15-08-0010 (see docs/ops/S21_TASK.md)
- [ ] 手順が 順序固定（並べ替え不要で実行できる）
- [ ] skip に has 必ず1行理由 を残すルールが入っている
- [ ] error は その場で終了 のルールが入っている

## 4) Dependency matrix 更新（依存と触る場所の確定）
- [ ] 各 step に以下が揃う：
  - DependsOn（先行が必要なら明記）
  - Touch（変更OKな files/dirs）
  - NoTouch（触ると設計凍結が壊れる場所）
  - Gate（docs-only or code-change）
  - PR unit（原則：1 step = 1 PR）
- [ ] DependsOn に 循環がない

## 5) 差分確認（想定外混入を殺す）
- [ ] git diff --stat が 3点のみ（PLAN/TASK/MATRIX）
- [ ] git diff を目視し、機械的ルールとDone条件が読めることを確認

## 6) ゲート（Eco）
- [ ] reviewpack submit --mode verify-only を実行
- [ ] docs-only でない差分が出た場合 → error (スコープ外)

## 7) コミット & PR
- [ ] ブランチ：s15-08-kickoff-impl-split-v1
- [ ] コミット：docs(s15-08): lock dependencies + PR slicing rules
- [ ] PR本文に「Done条件」「変更対象3点」「verify-only結果」を記載
