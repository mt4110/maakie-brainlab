# TASK: S17-03 FINALIZE Canonical Audit
Status: IN_PROGRESS
Owner: ambi
Progress: 0%

## 0) Snapshot (Must be Clean)
- [ ] cd "$(git rev-parse --show-toplevel)"
- [ ] git status -sb (Check: clean)
- [ ] git rev-parse HEAD (Check: 03108902475ec622596da49e060422e285ae4564) (If mismatch: error)

## 1) Canonical Fixation (135256 / 7f444f...)
- [ ] Update `docs/ops/S17-03_TASK.md` to canonical (0310890 / 135256 / 7f444f...)
- [ ] Update `docs/ops/S17-03_RETROFIX_TASK.md` to canonical (0310890 / 135256 / 7f444f...)
- [ ] Update `docs/evidence/s17-03/fix_summary.md` (remove contradictions, set canonical)
- [ ] Update `docs/evidence/s17-03/fix_evidence.txt` (separate canonical/historical)
- [ ] Update/Create `docs/reviewpack/WALKTHROUGH.md` with final canonical paragraph
- [ ] Update `.github/workflows/run_always_1h.yml` comments/if-condition (secrets based)

## 2) Gate (Zero Tolerance)
- [ ] `rg -n 'file://' .` (Must be 0 hits)
- [ ] `make test` (Must PASS)
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only` (Must PASS)
- [ ] `rg -n '03cc0575|review_bundle_20260215_121251'`
    - If found in historical section: SKIP
    - If found elsewhere: ERROR

## 3) Final Ritual (Push & PR)
- [ ] git add -A
- [ ] git commit -m "docs(s17-03): finalize canonical refs to 0310890 / 135256 / 7f444f"
- [ ] git push
- [ ] Update PR #51 body with canonical `135256` ritual
- [ ] Verify PR body via `gh pr view 51`
