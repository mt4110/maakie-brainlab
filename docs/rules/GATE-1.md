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
1. **Answer Structure**: Every answer produced by `src/ask.py` MUST include explicit sections with these headings: `結論:` and `参照:` and `不確実性:`. It SHOULD include `根拠:` when applicable. English labels may be included in addition, but the Japanese headings are canonical for review and stability.
2. **No Groundless Assertions**: Answers MUST be backed by a cited Source. If no source supports the answer, the system MUST state "Reference Unknown" or similar.
3. **Eval Integrity**: Evaluation (`run_eval.py`) MUST enforce `passed=True` and `details.has_sources=True` (or equivalent citation).
   - **Exception**: `negative_control` questions are EXEMPT from the sources requirement (they typically should NOT have sources).
4. **Scope Lock**: Tools and scripts MUST NOT modify files outside the repo's tracked files or the specific data subpaths they own.

## 4. Prohibitions (MUST NOT)
1. **Guessing**: Do not fill in missing data with "likely" values.
2. **Auto-Correction**: Do not automatically "fix" malformed data without an explicit audit log or user approval.
3. **Ignoring Gate Failure**: Do not proceed to deployment or merge if `make gate1` fails.

## 5. Exceptions
- **Explicit Override**: `negative_control` type questions do not require sources.
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
  - `make gate1` (または `bash ops/gate1.sh`) を実行して、上記チェックを全自動で行う。

### 検証専用モード (Verify-Only Mode)

レビューパック（review_pack）等の配布物において、実行環境が制限されている場合や過去の評価結果を再検証したい場合に利用する。

- **実行方法**: `bash ops/gate1.sh --verify-only`
- **挙動**:
    - `run-eval` を実行せず、`eval/results/latest.jsonl` を直接検証する。
    - ユニットテストや環境チェック（シンボリックリンク等）をスキップする。
    - 評価済みの「正しさの証跡」のみを確認する。
