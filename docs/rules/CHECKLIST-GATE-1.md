# S4.4 Gate-1 Checklist

## Pre-PR / Pre-Merge Check
- [ ] **Run Gate-1**: `make gate1` must PASS.
- [ ] **Scope Check**: No changes to `data/`, `index/`, `logs/`, `models/` structure (symlinks respected).
- [ ] **Eval Verification**:
    - [ ] `passed=True` for all relevant questions.
    - [ ] `details.has_sources=True` (or equivalent citation) is present for all answered questions (Exception: `negative_control` types).
- [ ] **Determinism**: Re-running yields consistent results under the same conditions; if drift occurs, record the cause (model parameters / external changes).

## Troubleshooting Gate-1 Failure
1. **Did `pytest` fail?**
    - Check unit test logs (`make test`). Fix strict logic bugs first.
2. **Did `eval` fail?**
    - Check `passed=False`: Model gave wrong answer.
    - Check `passed=True` but `gate1` failed: Model gave right answer **without details.has_sources=True** (Hallucination/Lucky Guess).
    - Check `latency`: Is the model responding?
3. **Did `symlinks` fail? (external links check)**
    - Run `ls -l data index logs models` to verify symlinks are active to external storage.
