# TASK: S17-03 Final Audit Closeout (Canonical Fixation)
Status: IN_PROGRESS
Owner: ambi
Progress: 0%

## Canonical (must not change)
- **See PR Body "Canonical Ritual" block** (to prevent infinite drift)

## 0) Snapshot (0%→10%)
- [ ] repo_root := `cd "$(git rev-parse --show-toplevel)"`
- [ ] branch := `git rev-parse --abbrev-ref HEAD` (Check: != main)
- [ ] `git status -sb` (Check: clean OR commit explicitly before gates)

## 1) Hygiene: file:/{2} ban (10%→25%)
- [ ] `rg -n 'file:/{2}' docs ops .github internal` (Check: 0 hits)
- [ ] If hits > 0: replace each `file:/{2}...` → `[FILE_URI]` (1 line reason in commit)
- [ ] Re-run the rg check (must be 0)

## 2) Drift Sweep: legacy canonical must not leak (25%→40%)
- [ ] `rg -n 'review_bundle_20260215_121251|03cc0575' docs ops .github internal` (Check: 0 hits outside docs/evidence/s17-03/)
- [ ] If found outside evidence: fix doc text to “Historical” OR remove mention
- [ ] Re-run (must be clean)

## 3) Canonical Pin: update all canonical blocks (40%→70%)
- [ ] Update `docs/ops/S17-03_TASK.md` canonical block to commit 0310890 / bundle 135256 / sha 7f444f...
- [ ] Ensure `docs/ops/S17-03_FINALIZE_PLAN.md` contains no file:/{2} and matches canonical
- [ ] Ensure `docs/ops/S17-03_FINALIZE_TASK.md` contains no file:/{2} and matches canonical
- [ ] Update:
  - [ ] `docs/evidence/s17-03/fix_evidence.txt`
  - [ ] `docs/evidence/s17-03/fix_summary.md`
  - [ ] `WALKTHROUGH.md`
  (All must state: verify-only outputs are Observation; canonical is commit-fixed)

## 4) Commit & PR body ritual (70%→85%)
- [ ] `git diff`
- [ ] `git add -A`
- [ ] `git commit -m "docs(s17-03): finalize canonical fixation (0310890/135256)"`
- [ ] `git push`
- [ ] Update PR #51 body “Canonical Ritual” block (commit/bundle/sha) + note about Observation runs

## 5) Gates (85%→100%)
- [ ] `make test` (Check: PASS)
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only` (Check: PASS)
- [ ] `git status -sb` (Check: clean)
- [ ] Mark Status: DONE / Progress: 100%

## Skip / Error rules
- skip: 1行で理由を書く（例: "skip: no changes needed; rg returned 0 hits"）
- error: その場で終了（例: "error: file:/{2} detected in tracked docs; must sanitize"）
