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
