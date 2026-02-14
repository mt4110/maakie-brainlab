# S16-02 TASK — Repo Absolute Plan/Task Standard (v1)

## Safety Snapshot
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git rev-parse --show-toplevel'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git log -1 --oneline --decorate'`

## Absolute Paths (MUST list)
- [ ] `bash -lc 'ROOT="$(git rev-parse --show-toplevel)"; printf "%s\n" "$ROOT/docs/ops/S16-02_PLAN.md" "$ROOT/docs/ops/S16-02_TASK.md" "$ROOT/docs/ops/S16-03_PLAN.md" "$ROOT/docs/ops/S16-03_TASK.md" "$ROOT/docs/ops/S16_PLAN.md" "$ROOT/docs/ops/S16_TASK.md"'`

## Author S16-02 docs
- [ ] Create/Update: docs/ops/S16-02_PLAN.md
- [ ] Create/Update: docs/ops/S16-02_TASK.md

## Update S16 index docs
- [ ] Update: docs/ops/S16_PLAN.md（S16-00..03固定、S16-02/03の目的追記）
- [ ] Update: docs/ops/S16_TASK.md（S16全体の実行順序の固定）

## Gate (MUST)
- [ ] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'`
- [ ] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'`

## Policy Scan (MUST)
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; rg -n "file""///" . || true'`
  - If hit > 0:
    - [ ] ERROR: remove links from repo/PR本文（スクラッチは repo 外のみ許容）

## Commit
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git add docs/ops/S16-02_PLAN.md docs/ops/S16-02_TASK.md docs/ops/S16_PLAN.md docs/ops/S16_TASK.md'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git commit -m "chore(docs): standardize repo-absolute plan/task (S16-02)"'`
