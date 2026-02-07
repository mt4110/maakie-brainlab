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
    - Check unit test logs. Fix strict logic bugs first.
2. **Did `eval` fail?**
    - Check `pass=False`: Model gave wrong answer.
    - Check `pass=True` but `gate1` failed: Model gave right answer **without sources** (Hallucination/Lucky Guess).
    - Check `latency`: Is the model responding?
3. **Environment/Link issues?**
    - Run `ls -l data index models` to verify symlinks are active.
