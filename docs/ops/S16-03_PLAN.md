# S16-03 PLAN — Ambi Precision Command Template (デグレ Fast Model v1)

## Goal
あんびちゃそが「毎回同じ型」で動くようにする。
速さは “思考量” ではなく “型” で出す（思考の最大化ではなく、再現性の最大化）。

## Core Idea
- **Safety Snapshot → 探索 → 最小修正 → Gate → Evidence → PR**
- for探索で迷いを潰す（見つけたら break / 無ければ continue）
- skip は理由1行、error は即終了（嘘を排除）

## Template (Pseudo Code)
PHASE 0: Safety Snapshot
  - branch / clean / last commit / repo root
  - dirtyなら ERROR

PHASE 1: Discover (for-search)
  - 目的に関係するファイル候補を列挙
  - rg/ls で存在確認
  - 見つけたら break
  - 見つからなければ SKIP(reason) or ERROR（仕様次第）

PHASE 2: Minimal Change Strategy
  - まず failing test を作る（再現性）
  - 修正は最小差分
  - 余計な整形・リファクタは別フェーズ

PHASE 3: Gates
  - make test
  - reviewpack submit --mode verify-only
  - 必要なら review_bundle SHA256 を evidence として記録

PHASE 4: Evidence + Narrative
  - 何を変えたか（SOT）
  - 何を確認したか（Gate）
  - 何を出力したか（bundle + sha）

## Acceptance Criteria
- docs/ops/S16-03_PLAN.md / TASK.md が存在
- “型” が docs に明記され、コマンドが再現可能
- make test / verify-only が PASS
