# S4.4 Gate-1 Checklist

## Pre-PR / Pre-Merge Check
- [ ] **Run Gate-1**: `make gate1` must PASS.
- [ ] **Scope Check**: No changes to `data/`, `index/`, `models/` structure (symlinks respected).
- [ ] **Eval Verification**:
    - [ ] `passed=True` for all relevant questions.
    - [ ] `details.has_sources=True` (or equivalent citation) is present for all answered questions (Exception: `negative_control` types).
- [ ] **Determinism**: Running the pipeline/eval twice yields consistent results.

## Troubleshooting Gate-1 Failure
1. **Did `pytest` fail?**
    - Check unit test logs (`make test`). Fix strict logic bugs first.
2. **Did `eval` fail?**
    - Check `passed=False`: Model gave wrong answer.
    - Check `passed=True` but `gate1` failed: Model gave right answer **without details.has_sources=True** (Hallucination/Lucky Guess).
    - Check `latency`: Is the model responding?
3. **Did `links` fail?**
    - Run `ls -l data index models` to verify symlinks are active to external storage.
