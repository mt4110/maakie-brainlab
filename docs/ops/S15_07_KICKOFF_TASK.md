# S15-07 kickoff TASK (07-10 design freeze)

## C0: Preflight
- [ ] cd repo root
- [ ] git status clean (or explicitly note dirty reason and STOP)
- [ ] create branch: s15-07-kickoff-07-10-design-v1

## C1: Discovery (facts)
- [ ] list docs/ops for S15-07..10 (name variants)
- [ ] rg S15-07..10 in S15_PLAN.md / S15_TASK.md
- [ ] collect titles/intent lines (paste into matrix draft)

## C2: Create/Normalize docs
- [ ] ensure kickoff plan/task files exist
- [ ] ensure dependency matrix file exists
- [ ] for each step (07..10):
  - [ ] plan exists, aligned to template sections
  - [ ] task exists, ordered checkboxes + STOP conditions
  - [ ] plan contains TouchSet + Dependencies (explicit)

## C3: Mechanical decision
- [ ] fill dependency edges in matrix
- [ ] mark TouchSet overlap yes/no
- [ ] write final decision:
  - [ ] "1 PR per step" OR "allow 07+08 / 09+10"

## C4: Consistency
- [ ] rg for broken references (missing file paths)
- [ ] confirm S15_PLAN.md / S15_TASK.md references still correct

## C5: Commit + PR
- [ ] git add docs/ops
- [ ] commit: docs(s15): kickoff 07-10 design freeze
- [ ] push branch
- [ ] gh pr create (docs-only)
