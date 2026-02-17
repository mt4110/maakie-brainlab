# S20-04 Mixed Hallucination & Negative Control Walkthrough

This change implements stricter evaluation logic to detect subtle hallucinations and enforce negative control compliance.

## Key Changes

### 1. New Failure Codes
Added to `eval/run_eval.py`:
- `MIXED_HALLUCINATION`: Triggered when an answer contains keywords (nouns/proper nouns) not found in the Evidence or Query, suggesting partial fabrication.
- `NEGATIVE_CONTROL_VIOLATION`: Triggered when a `negative_control` question receives a definitive answer instead of a refusal/unknown response.

### 2. Detection Logic (`eval/run_eval.py`)
- **Mixed Hallucination**:
  - Extracts keywords from `結論` (Conclusion) and `根拠` (Evidence).
  - Matches against `query` keywords.
  - If new terms appear in Conclusion without grounding in Evidence or Query -> **FAIL**.
- **Negative Control**:
  - Enforces "Unknown" response.
  - Checks for "However..." clauses (e.g., "Unknown, but typically...") -> **FAIL**.
  - Checks for hallucinated keywords even if "Unknown" is asserted.
  - **Hard Fail on Sources**: If sources are present, it is a Positive Hallucination (even if "Unknown" is stated).

### 3. Verification
Run the verification suite:
```bash
# Python Logic Tests
python -m unittest tests.test_eval_logic

# Full Reviewpack Check
go run cmd/reviewpack/main.go submit --mode verify-only
```

## Results
- **Python Tests**: Passed (7 tests covering normal, boundary, mixed hallucination, and negative control scenarios).
- **Go Validate**: Passed.
- **Reviewpack**: Passed strict checks.
