# S4.4 Gate-1: The Constitution (Rules)

> [!IMPORTANT]
> **Primary Directive:** Do not lie. Do not guess. Stop if unsure.

## 1. Scope
This repository manages the orchestration and logic for the Brainlab Satellite system.
The following directories are **strictly external links** (managed outside this repo code):
- `data/` (Raw/Normalized data storage)
- `index/` (Vector database artifacts)
- `logs/` (Server/Execution logs)
- `models/` (LLM weights/GGUF files)

Code in this repo MUST NOT assume ownership of these paths or attempt to "clean" them broadly. It MAY only write to specific subpaths defined by the pipeline (e.g., `data/satellite/{source_id}/...`).

## 2. Definitions
- **Evidence**: Verifiable artifacts produced by execution (e.g., `eval/results/*.jsonl`, logs).
- **Source / Citation**: A specific reference to a data chunk (e.g., `data/satellite/src/raw/2023-10-06.json#chunk-0`).
- **Determinism**: The property that the same input yields the same output. If deviation occurs, it must be explainable (e.g., model temperature, external feed change).
- **Fail Closed**: When a component encounters an unknown state or failure, it must **stop or return failure**, rather than returning a "best guess" or hallucination.

## 3. Invariants (MUST)
1. **Answer Structure**: Every answer produced by `src/ask.py` MUST maintain the structure of `Conclusion`, `Evidence` (Citation), `Uncertainty`.
2. **No Groundless Assertions**: Answers MUST be backed by a cited Source. If no source supports the answer, the system MUST state "Reference Unknown" or similar.
3. **Eval Integrity**: Evaluation (`run_eval.py`) MUST enforce `sources=True`. An answer that is "correct" but lacks sources is a **FAILURE**.
4. **Scope Lock**: Tools and scripts MUST NOT modify files outside the repo's tracked files or the specific data subpaths they own.

## 4. Prohibitions (MUST NOT)
1. **Guessing**: Do not fill in missing data with "likely" values.
2. **Auto-Correction**: Do not automatically "fix" malformed data without an explicit audit log or user approval.
3. **Ignoring Gate Failure**: Do not proceed to deployment or merge if `make gate1` fails.

## 5. Exceptions
- **Explicit Override**: If a specific evaluation question allows "General Knowledge" (no source), it must be explicitly tagged in `eval/questions.jsonl` (e.g., `requires_source: false`).
- **Logging**: All exceptions (allowed or failed) MUST be logged to `logs/` or stdout.

## 6. Decision Flow
- **Is there a CITATION?**
    - YES: Proceed to answer.
    - NO: Return "Unknown/Unanswerable".
- **Did Eval PASS?**
    - YES (All Pass + Sources Present): Gate-1 PASS.
    - NO (Any Fail OR Missing Source): Gate-1 FAIL. Stop immediately.

## 7. Operations
- **Run Gate-1**: `make gate1`
- **On Failure**:
    1. Check `ops/gate1.sh` output.
    2. If `pytest` failed: fix the code.
    3. If `eval` failed: check `eval/results/` for the specific failure (Wrong Answer vs Missing Source).
