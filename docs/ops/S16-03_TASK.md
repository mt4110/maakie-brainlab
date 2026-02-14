# S16-03 TASK — Ambi Precision Command Template (Degre Fast Model v1)

## Safety Snapshot
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git rev-parse --abbrev-ref HEAD'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git log -1 --oneline --decorate'`

## Author S16-03 docs
- [ ] Create/Update: docs/ops/S16-03_PLAN.md
- [ ] Create/Update: docs/ops/S16-03_TASK.md

## Gates
- [ ] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'`
- [ ] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'`

## Commit
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git add docs/ops/S16-03_PLAN.md docs/ops/S16-03_TASK.md'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git commit -m "chore(docs): add ambi precision command template (S16-03)"'`
