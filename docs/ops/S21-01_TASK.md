# S21-01 TASK — Outer Wall Triage v1

## Progress Snapshot (SOT)
- SnapshotDate: 2026-02-18
- done=323
- todo=576
- total=899
- progress=35.93%

## Implement Scaffold Files <!-- id: 3 -->
    - [x] [T1] Triage v1 (Top-10 files) <!-- id: T1 -->
    - [x] Migrate first 10 items to S21_TASK.md
    - [x] Replace with MIGRATED: references
    - [x] `docs/ops/S21_PLAN.md` <!-- id: 4 -->
    - [x] `docs/ops/S21_TASK.md` <!-- id: 5 -->
    - [x] `docs/ops/S21-01_PLAN.md` <!-- id: 6 -->
    - [x] `docs/ops/S21-01_TASK.md` <!-- id: 7 -->
    - [x] `docs/ops/STATUS.md` <!-- id: 8 -->

## STATUS (外壁)
- [x] else: S21 / S21-01 行を追加する
- [x] STATUS に “NEXT（次に触る）” が必ず1個以上ある状態にする

## Mechanical Evidence (No-Exit)
- [x] TODOホットスポット（ファイル別件数）を再採取して貼る（上位だけでOK）
    - docs/ops/S8_TASK.md: 10 items
    - docs/ops/S18-00_TASK.md: 10 items
    - ... (Total 10 files processed in Triage v1)
- [x] hot todos 抽出（S8/S15/S18-00/S19-01/S16-01）を再採取して貼る（先頭だけでOK）
    - Verified: S21_TASK.md now contains Top-10 file extractions.

## Triage v1 (小さく勝つ)
- [x] Top-1（例: S8_TASK）から先頭K件だけ移植する（K=10 推奨）
  - [x] for each todo:
      - [x] MIGRATE: S21_TASK Backlog に checkbox として1行追加
      - [x] origin 側は checkbox を消し、参照行（MIGRATED: ...）に置換
- [x] STATUS を更新（ACTIVE/NEXT/PARKED/GRAVEYARD が機能していること）

## Verification (軽いものだけ)
- [x] git status -sb で差分が doc中心であることを確認
- [x] rg で “exit / set -e / sys.exit / SystemExit / assert” が docs/ops に新規混入してないことを確認

## Commit / PR
- [x] commit: "docs(ops): add S21 outer wall triage scaffold (S21-01)"
- [x] PR body に SOT と Snapshot を貼る (Bundle: review_bundle_20260218_120357.tar.gz)
