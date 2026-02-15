# TASK: S17-03 FINALIZE Canonical Audit
Status: DONE
Owner: ambi
Progress: 100%

## 0) Snapshot (Must be Clean)
- [x] cd "$(git rev-parse --show-toplevel)"
- [x] git status -sb (Check: clean)
- [x] git rev-parse HEAD (Check: 03108902475ec622596da49e060422e285ae4564) (If mismatch: error)

## 1) Canonical Fixation (135256 / 7f444f...)
- [x] Update `docs/ops/S17-03_TASK.md` to canonical (0310890 / 135256 / 7f444f...)
- [x] Update `docs/ops/S17-03_RETROFIX_TASK.md` to canonical (0310890 / 135256 / 7f444f...)
- [x] Update `docs/evidence/s17-03/fix_summary.md` (remove contradictions, set canonical)
- [x] Update `docs/evidence/s17-03/fix_evidence.txt` (separate canonical/historical)
- [x] Update/Create `docs/reviewpack/WALKTHROUGH.md` with final canonical paragraph
- [x] Update `.github/workflows/run_always_1h.yml` comments/if-condition (secrets based)

## 2) Gate (Zero Tolerance)
- [x] `rg -n '[FILE_URI]' .` (Must be 0 hits)
- [x] `make test` (Must PASS)
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only` (Must PASS)
- [x] `rg -n '03cc0575|review_bundle_20260215_121251'`
    - If found in historical section: SKIP
    - If found elsewhere: ERROR

## 3) Final Ritual (Push & PR)
- [x] git add -A
- [x] git commit -m "docs(s17-03): finalize canonical refs to 0310890 / 135256 / 7f444f"
- [x] git push
- [x] Update PR #51 body with canonical `135256` ritual
- [x] Verify PR body via `gh pr view 51`
