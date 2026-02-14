# S16 Task: AI Contract Kickoff (Finalized Order)

## S16-00: Kickoff
- [x] Initial contract design and docs/ops check

## S16-01: Enforcement
- [x] Enforce AI Contract V1 (reviewpack main/verify-only)

## S16-02: Plan/Task Standard
- [ ] Create/Update: docs/ops/S16-02_PLAN.md
- [ ] Create/Update: docs/ops/S16-02_TASK.md
- [ ] Gate (S16-02): `bash -lc 'cd "$(git rev-parse --show-toplevel)"; PAT="$(printf "%c%c%c%c%c%c%c" 102 105 108 101 58 47 47)"; if git ls-files -z | xargs -0 rg -n "$PAT"; then echo "[FAIL] forbidden file URL found" >&2; exit 1; else echo "[OK] none"; fi'`

## S16-03: Command Template
- [ ] Create/Update: docs/ops/S16-03_PLAN.md
- [ ] Create/Update: docs/ops/S16-03_TASK.md

## S16 Final Gate (MUST)
- [ ] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'`
- [ ] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; PAT="$(printf "%c%c%c%c%c%c%c" 102 105 108 101 58 47 47)"; if git ls-files -z | xargs -0 rg -n "$PAT"; then echo "[FAIL] forbidden file URL found" >&2; exit 1; else echo "[OK] none"; fi'`

## Final PR Updates
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git add docs/ops/S16_PLAN.md docs/ops/S16_TASK.md docs/ops/S16-02_PLAN.md docs/ops/S16-02_TASK.md'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git commit -m "chore(docs): lock S16 milestones + fix file-url scan recipe"'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git push'`
