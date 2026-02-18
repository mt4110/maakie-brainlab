# S21-02 Ops Hygiene — Milestone/Exception Discipline + PR Template Hardening

## Goal
To stabilize milestone-related WARN/FAIL fluctuations by absorbing "human habits" into templates and procedures. The goal is to make the process robust through "unconscious" compliance via templates, while preserving human judgment in the PR body audit log.

## Deliverables
- `docs/ops/S21-02_PLAN.md`
- `docs/ops/S21-02_TASK.md`
- `.github/pull_request_template.md` (Add Milestone/Exception fields)
- `docs/ops/PR_WORKFLOW.md` (Update Milestone operations section)
- `docs/ops/STATUS.md` (Add S21-02 entry)

## Invariants (The Outer Wall)
1. **Milestone Obligation**: A PR MUST either have a Milestone set OR have `no-milestone-ok` label AND a non-empty Exception reason.
2. **No Empty Fields**: PR body fields must be filled. The template prevents "blank" submissions by guiding the user.
3. **Audit Log**: Every decision (milestone choice or exception) must be recorded in the PR body.

## Design (Pseudocode / Audit-First)

```python
if pr.has_milestone():
    milestone_required = "PASS"
    milestone_advisory = "clean"
else:
    if label == "no-milestone-ok" and exception_reason is not empty:
        milestone_required = "SKIP"
        milestone_advisory = "clean"
    else:
        milestone_required = "FAIL/WARN" # Follow existing behavior
```

**Every decision must be written in PR body.**

## Evidence
- `git diff` shows changes restricted to `docs/ops/*` and `.github/pull_request_template.md`.
- PR body follows SOT (Source of Truth) style with no empty fields.
- `reviewpack verify-only` PASS (optional, strictly verify-only).
