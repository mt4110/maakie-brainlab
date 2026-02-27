# S21-02 Task: Milestone Discipline + PR Template Hardening

- [x] **Preflight**
    - [x] Check Repo Root (Observer: `REPO=...` or ERROR)
    - [x] Check Git Status (Observer: `git status -sb` must not be dirty)

- [x] **Implementation**
    - [x] Create `docs/ops/S21-02_PLAN.md`
    - [x] Create `docs/ops/S21-02_TASK.md`
    - [x] Update `.github/pull_request_template.md`
        - [x] Add Milestone selection / Exception reason field
        - [x] Add instruction for "WARN remaining"
    - [x] Update `docs/ops/PR_WORKFLOW.md`
        - [x] Document rule: Milestone OR (no-milestone-ok + Reason)
        - [x] Explain `milestone_required` / `milestone_advisory`
        - [x] Mandate no empty fields in PR body
    - [x] Update `docs/ops/STATUS.md` (Add S21-02 row, start at 0%)

- [x] **Snapshot**
    - [x] Update progress in `S21-02_TASK.md`

- [x] **Verification**
    - [x] **Verify(light)**: `git diff --name-only origin/main...HEAD` (Expect only docs & template)
    - [x] **Verify(light)**: Markdown lint (delegated to CI)
    - [x] **Verify(heavy)**: `go run cmd/reviewpack/main.go submit --mode verify-only` (Optional, once at end)
