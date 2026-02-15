# TASK: S17-03 RETROFIX Audit Consistency
Status: IN_PROGRESS
Owner: ambi
Progress: 0%

## 0) Snapshot
- [ ] cd "$(git rev-parse --show-toplevel)"
- [ ] git rev-parse --abbrev-ref HEAD is not main
- [ ] git status -sb is clean

## 1) Canonical bundle Verification
- [ ] BUNDLE=".local/review-bundles/review_bundle_20260215_121251.tar.gz"
- [ ] shasum -a 256 "$BUNDLE" matches 03cc0575...416fff

## 2) PASS run artifacts
- [ ] gh run view 22027976749 --log > docs/evidence/s17-03/log_pass_22027976749.txt
- [ ] gh run view 22027976749 --json databaseId,status,conclusion,event,createdAt,updatedAt,headSha,headBranch,workflowName,url > docs/evidence/s17-03/run_22027976749.json

## 3) fix_evidence.txt Repair
- [ ] Edit `docs/evidence/s17-03/fix_evidence.txt` with run refs and canonical info.

## 4) S17-03_TASK.md Patch
- [ ] Unified bundle name and SHA in `docs/ops/S17-03_TASK.md`
- [ ] Replace absolute paths with portable links

## 5) fix_summary.md Patch
- [ ] Update `docs/evidence/s17-03/fix_summary.md` with canonical info.

## 6) Milestone Rollup
- [ ] Align `docs/ops/S17_PLAN.md` Status/Progress
- [ ] Align `docs/ops/S17_TASK.md` Status/Progress

## 7) run_always Hardening
- [ ] Log `SIGNING_MODE=SMOKE` or `REAL` in `ops/run_always_1h.sh`

## 8) Gates
- [ ] make test
- [ ] go run cmd/reviewpack/main.go submit --mode verify-only (bundle sha 03cc...)
- [ ] CI=true ops/run_always_1h.sh (if possible)

## 9) Commit / Push
- [ ] Final commit and PR body update
