# IL_COUNCIL_CONTRACT_v1

## Purpose
Define a safe, deterministic multi-model council interface that can be inserted later.
This document is design-only (no implementation requirement).

## Core Principle
- Council is an optional **planner-of-plans**.
- Council must never directly execute opcodes or touch external side effects.
- Council produces artifacts that are audit-friendly and reproducible.

## IL Opcodes (Design)
### COUNCIL_PLAN
Input: a normalized IL request + context metadata  
Output: a deterministic council plan describing:
- which models to consult
- prompts/roles per model
- aggregation method
- budget/time limits

### COUNCIL_RUN
Input: COUNCIL_PLAN + sealed inputs  
Output: per-model outputs saved as immutable artifacts.

### COUNCIL_DECIDE
Input: all per-model outputs  
Output: final decision IL (single canonical IL) + rationale + dissent notes.

## Determinism Rules
- Inputs MUST be normalized/canonicalized before council.
- Model selection MUST be explicit and recorded.
- Temperature/settings MUST be fixed and recorded.
- Aggregation order MUST be fixed (stable sort by model_id).

## Safety Guardrails
- Hard limits:
  - max_models: 3 (default)
  - max_total_cost: configurable (default small)
  - max_wall_time: configurable (default small)
- If limit exceeded: produce `SKIP` with reason (no crash).
- No network access unless explicitly permitted by policy (default deny).
- No writes outside `.local/obs/...` (design default).

## Artifacts (Required)
- council_plan.json
- council_votes.jsonl (per-model)
- council_decision.json
- council_audit.json (limits, timing, settings, hashes)
- SHA256SUMS.txt (deterministic ordering)

## Failure Handling (Stopless)
- Do not raise / sys.exit / assert.
- Record:
  - OK / ERROR / SKIP lines
  - reason for SKIP
  - last successful observation
