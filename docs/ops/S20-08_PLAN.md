# DETERMINISTIC_PLAN_TEMPLATE (v1)

## Goal
- {{GOAL_ONE_LINE}}

## Invariants (Must Hold)
- Planは分岐と停止条件（嘘をつかない）
- Canonicalは1回だけ固定（以降はObservations）
- skipは理由1行、errorはその場で停止
- 編集対象は実パス固定（探索→確定→記録）

## Inputs (SOT)
- {{SOT_PATHS}}

## Outputs (Deliverables)
- {{DELIVERABLES}}

## Gates
- make test PASS
- go run cmd/reviewpack/main.go submit --mode verify-only PASS

## Phase 0 — Scope Definition (STOP条件つき)
- if scope missing:
  - error: "scope missing; define explicitly before coding"

## Phase 1 — Define Deliverables
- Deliverable A: {{A}}
- Deliverable B: {{B}}

## Phase 2 — Implementation
- smallest safe steps + local gates

## Phase 3 — Final Gate & Canonical Pin (single)
- pin once: commit / bundle / sha256
- note: future verify-only outputs are Observations

## Phase 4 — PR Ritual
- Canonical block is written exactly once
