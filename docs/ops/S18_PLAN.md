# S18 PLAN — Deterministic (v1)

## Goal
- S18: Deterministic Operation Standards (Ops Bootstrap & Hardening)

## Scope
- **S18-00: Template kit bootstrap** (this PR)
- **S18-01+: TBD** (must be defined in ops docs before starting)

## Invariants (Must Hold)
- Planは **分岐と停止条件**（嘘をつかない）
- Canonicalは **1回だけ固定**（以降はObservations）
- skipは理由を1行、errorはその場で停止（握りつぶし禁止）
- 実装対象ファイルは **実パス固定**（探索→確定→記録）

## Inputs
- docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md
- docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md

## Gates
- make test PASS
- go run cmd/reviewpack/main.go submit --mode verify-only PASS

## Phases (Additions)
- S18-01: Phase Scaffold Generator v1 — scope pinned; implementation allowed
