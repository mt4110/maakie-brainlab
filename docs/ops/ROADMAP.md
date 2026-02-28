# docs/ops ROADMAP (入口)

迷ったらまずここ。**“何を見れば何が分かるか”**を固定する。

## 最短回答（どれを見る？）

- **全体図（そのSシリーズの設計と到達点）** → docs/ops/S<番号>_PLAN.md（例: docs/ops/S19_PLAN.md）

- **実行チェックリスト（今やること / 手順 / Gate）** → docs/ops/S<番号>_TASK.md（例: docs/ops/S19_TASK.md）

- **シリーズ内フェーズ（分割作業）** → docs/ops/S<番号>-<番号>_PLAN.md / ..._TASK.md（例: docs/ops/S20_PLAN.md）

- **横断ルール（凡例）** → `docs/ops/PR_WORKFLOW.md` / `docs/ops/CI_REQUIRED_CHECKS.md` / repo ルート `SPEC.md`

- **今の地点（branch + task + progress + 次アクション）** → `make ops-now`

## シリーズ俯瞰（自動生成）

### S7 — Historical
- 全体図: `docs/ops/S7_PLAN.md`

### S8 — Historical
- 全体図: `docs/ops/S8_PLAN.md`
- 実行: `docs/ops/S8_TASK.md`

### S9 — Historical
- 全体図: `docs/ops/S9_PLAN.md`
- 実行: `docs/ops/S9_TASK.md`

### S15 — Historical
- 全体図: `docs/ops/S15_PLAN.md`
- 実行: `docs/ops/S15_TASK.md`

### S16 — Historical
- 全体図: `docs/ops/S16_PLAN.md`
- 実行: `docs/ops/S16_TASK.md`

### S17 — Historical
- 全体図: `docs/ops/S17_PLAN.md`
- 実行: `docs/ops/S17_TASK.md`

### S18 — Historical
- 全体図: `docs/ops/S18_PLAN.md`
- 実行: `docs/ops/S18_TASK.md`

### S19 — Done ✅（S19 docs はS20で実態化）
- 全体図: `docs/ops/S19_PLAN.md`
- 実行: `docs/ops/S19_TASK.md`

### S20 — Done ✅
- 全体図: `docs/ops/S20_PLAN.md`
- 実行: `docs/ops/S20_TASK.md`

### S21 — Active
- 全体図: `docs/ops/S21_PLAN.md`
- Phase 01-07: `docs/ops/S21-0x_PLAN.md` (See STATUS.md for breakdown)

### S22 — Active
- 全体図: `docs/ops/S22_PLAN.md` (derived from `S22-01..S22-20`)
- S22-01: Done ✅ (Merged PR #76)
- S22-02: WIP (Review PR #77)
- S22-03: Done ✅ (Merged PR #78)
- S22-04: Done ✅ (Merged PR #79)
- S22-05: Done ✅ (Merged PR #81)

### S23 — Done ✅
- 全体図: `docs/ops/S23-01_PLAN.md` ... `docs/ops/S23-10_PLAN.md`
- 実行: `docs/ops/S23-01_TASK.md` ... `docs/ops/S23-10_TASK.md`

### S24 — Active (Thread v1)
- 全体図: `docs/ops/S24-01-S24-10-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S24-01-S24-10-THREAD-V1_TASK.md`

### S25 — Done ✅ (Thread v1)
- 全体図: `docs/ops/S25-01-25-10-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S25-01-25-10-THREAD-V1_TASK.md`

### S26 — Active (Thread v1: S26-01..S26-10)
- 全体図: `docs/ops/S26-01-S26-02-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S26-01-S26-02-THREAD-V1_TASK.md`

### S27 — Active (Thread v1: S27-01..S27-10)
- 全体図: `docs/ops/S27-01-S27-10-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S27-01-S27-10-THREAD-V1_TASK.md`

### S28 — Active (Thread v5: S28-01..S28-10)
- 全体図: `docs/ops/S28-01-S28-10-THREAD-V5_PLAN.md`
- 実行: `docs/ops/S28-01-S28-10-THREAD-V5_TASK.md`

### S29 — Active (Thread v3: S29-01..S29-10)
- 全体図: `docs/ops/S29-01-S29-10-THREAD-V3_PLAN.md`
- 実行: `docs/ops/S29-01-S29-10-THREAD-V3_TASK.md`

### S30 — Active (Thread v1: S30-1..S30-900)
- 全体図: `docs/ops/S30-1-S30-900-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S30-1-S30-900-THREAD-V1_TASK.md`

### S31 — Active (Thread v1: S31-01..S31-30)
- 全体図: `docs/ops/S31-01-S31-30-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S31-01-S31-30-THREAD-V1_TASK.md`
- 実装プロンプト: `docs/ops/S31-01-S31-30-THREAD-V1_PROMPTS.md`

### S32 — Active (Thread v1: S32-01..S32-30)
- 全体図: `docs/ops/S32-01-S32-30-THREAD-V1_PLAN.md`
- 実行: `docs/ops/S32-01-S32-30-THREAD-V1_TASK.md`
- 実装プロンプト: `docs/ops/S32-01-S32-30-THREAD-V1_PROMPTS.md`

### S33 — Planned (Handoff Ready)
- 起点資料: `docs/evidence/s32-30/handoff_latest.json`
- 初期バックログ: `docs/evidence/s32-29/s33_backlog_seed_latest.json`
