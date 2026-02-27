# S16-03 TASK — Ambi Precision Command Template (デグレ Fast Model v1)

## Safety Snapshot
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'`
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git rev-parse --abbrev-ref HEAD'`
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git log -1 --oneline --decorate'`

## Author S16-03 docs
- [x] Create/Update: docs/ops/S16-03_PLAN.md
- [x] Create/Update: docs/ops/S16-03_TASK.md

## Gates
- [x] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'`
- [x] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'`

## Commit
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git add docs/ops/S16-03_PLAN.md docs/ops/S16-03_TASK.md'`
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git commit -m "chore(docs): add ambi precision command template (S16-03)"'`
