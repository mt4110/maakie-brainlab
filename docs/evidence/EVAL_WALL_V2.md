# Eval Wall v2 Contract & Taxonomy

## Execution Mode Contract (The Pitfall Killer)

To ensure measurement determinism, the following execution modes are strictly defined:

- **`validate-only`**:
  * MUST NOT call executor or execute opcodes.
  * MUST NOT perform network operations.
  * MUST NOT perform writes outside `.local/obs/` (ideally no writes at all).
  * Its purpose is pure analysis and fast failure classification.

- **`run`**:
  * Allowed writes are strictly confined to the OBS directory (`.local/obs/...`).
  * MUST produce the resulting `JSONL` and `summary.json` conforming to a fixed schema.

- **Determinism Scope**:
  * The exact same input + same tool version + same flags **MUST** yield the exact same JSONL sha256 hash.

## Classification & Measurement (TAXONOMY_v1)

We define **classify** as the assignment of a failure tag from the following canonical taxonomy list, and **measure** as tallying these tags in `summary.json`.

**Failure Tags (TAXONOMY_v1):**
- `schema`: Format does not match JSON schema.
- `contract`: Violates logical contract (e.g., float instead of int).
- `opcode`: Attempted to call an unknown or unauthorized opcode.
- `normalization`: Payload normalization failed (e.g., cannot fetch external resource).
- `index`: Failure during RAG DB creation/indexing.
- `search`: RAG sequence or search logic threw a runtime error.
- `cite`: Citation format was malformed or missing required evidence.

## Determinism Evidence (S22-09 Smoke Tests)
The deterministic measurement of `summary.json` and `cases.jsonl` was successfully verified on the `il-eval-wall-v2__seed-mini__v0001` (N=20) dataset using `run1` and `run2` testing.
Commands executed via `eval_wall_v2_il_centered.py` and subsequently `eval_wall_v2_postprocess_cases.py` consistently produce identical output file hashes across runs.

Example Evidence (`N=20`, observed `20260224T052939Z`):
- `summary.json` SHA256: `0f0c69ca65fa51e9b0de4e866abd915c1d5bcc4166b2c2e62002481d4a63ddb0`
- `cases.jsonl` SHA256: `700341a9807a3bac93ec548d170fe7d7a414f0af926935a5f93d02b403160e50`
- Audit context available at OBS path: `.local/obs/s22-09_smoke_pp_n20_20260224T052939Z`

## Validate-only Structural Audit (AST Evidence)

Observed: s22-09_ast_audit_20260224T062520Z
- OBS: `.local/obs/s22-09_ast_audit_20260224T062520Z`
- ast_audit.log sha256: `81e248aeeacd9176579407a9ab9b81092a5f127c327c501b893922026dafed5c`

## Taxonomy Upgraded Determinism (Precision Evaluation)

Observed: s22-09_smoke_pp_n20_20260224T062727Z
- `summary.json` SHA256: `0f0c69ca65fa51e9b0de4e866abd915c1d5bcc4166b2c2e62002481d4a63ddb0`
- `cases.jsonl` SHA256: `700341a9807a3bac93ec548d170fe7d7a414f0af926935a5f93d02b403160e50`
- Audit context CPU available at OBS path: `.local/obs/s22-09_smoke_pp_n20_20260224T062727Z`
