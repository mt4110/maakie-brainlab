# MULTIMODEL_POLICY_v1

## Scope
Operational policy for inserting a multi-model council into evaluation/IL workflow.

## When Council is Triggered
Council is triggered only when at least one condition holds:
- repeated failure classification ambiguity (taxonomy_tag flips across runs)
- citation requirement mismatch that a single model cannot resolve
- operator requests escalation explicitly

Default: council disabled.

## Cost/Time Limits
- max_models: 3
- max_wall_time_seconds: 60 (default)
- max_total_cost_units: low default
If exceeded → SKIP with reason.

## Data Handling
- Inputs must be canonicalized.
- Outputs are stored only under `.local/obs/...`.
- No secrets in prompts; sanitize environment paths.

## Audit Requirements
Every council run must record:
- model IDs + settings
- prompt hashes
- aggregation method
- artifact hashes
- final decision hash

## Non-Execution Contract
Council must never execute:
- executor/opcodes
- network operations
- file writes outside OBS
