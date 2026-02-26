# S22-19 PLAN — Ship Automation Generalization
Last Updated: 2026-02-26

## Goal
- `S22-16`専用 ship フローを phase 再利用可能にする。

## Acceptance Criteria
- phase 指定で実行できる汎用 ship helper を追加する。
- 既存の guard/verify-il/ci-self gate/PR同期フローを継承する。
- `.local` と review bundle tarball を自動で stage 除外できる。
- `Makefile` から phase 指定実行できる。

## Impacted Files
- `ops/phase_ship.py`
- `Makefile`
- `docs/ops/S22-19_PLAN.md`
- `docs/ops/S22-19_TASK.md`

## Design
- `--phase S22-19` を主入力にした generic CLI。
- phase 未指定時は branch 名 `sNN-NN` から推測。
- 既存運用と同じく `ci-self up --ref <branch>` を PR同期前 gate とする。

