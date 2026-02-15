# TASK: S17-03 RETROFIX Audit Consistency
Status: DONE
Owner: ambi
Progress: 100%

## 0) Snapshot (Must be Clean)
- [ ] cd "$(git rev-parse --show-toplevel)"
- [ ] git status -sb is clean
- [ ] rg -n "eb8631|124326" docs/ops docs/evidence || true (Assess presence of non-canonical SHA)

## 1) Canonical Fixation (0310890 / 135256)
- [ ] Update `docs/ops/S17-03_TASK.md` to use `135256` / `7f444f...`
- [ ] Update `docs/evidence/s17-03/fix_summary.md` to use `135256` / `7f444f...`
- [ ] Ensure `docs/evidence/s17-03/fix_evidence.txt` uses `135256` / `7f444f...`

## 2) Documentation Completion
- [ ] Set `docs/ops/S17-03_RETROFIX_PLAN.md` to Status: DONE / Progress: 100%
- [ ] Set `docs/ops/S17-03_RETROFIX_TASK.md` to Status: DONE / Progress: 100%

## 3) Consistency Gate (Zero Tolerance)
- [ ] `rg -n "eb8631|124326" docs/ops docs/evidence` must return 0 hits
- [ ] `rg -n "Status: IN_PROGRESS|Progress: 0%" docs/ops/S17-03*` must return 0 hits

## 4) Final Ritual
- [ ] make test
- [ ] Commit (chore/docs)
- [ ] Push
- [ ] Update PR #51 body with canonical `135256` ritual
- [ ] Verify PR body via `gh pr view 51`
