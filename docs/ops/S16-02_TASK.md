# S16-02 TASK — Repo Absolute Plan/Task Standard (v1)

## Safety Snapshot
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'`
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git rev-parse --show-toplevel'`
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git log -1 --oneline --decorate'`

## Absolute Paths (MUST list)
- [x] `bash -lc 'ROOT="$(git rev-parse --show-toplevel)"; printf "%s\n" "$ROOT/docs/ops/S16-02_PLAN.md" "$ROOT/docs/ops/S16-02_TASK.md" "$ROOT/docs/ops/S16-03_PLAN.md" "$ROOT/docs/ops/S16-03_TASK.md" "$ROOT/docs/ops/S16_PLAN.md" "$ROOT/docs/ops/S16_TASK.md"'`

## Author S16-02 docs
- [x] Create/Update: docs/ops/S16-02_PLAN.md
- [x] Create/Update: docs/ops/S16-02_TASK.md

## Update S16 index docs
- [x] Update: docs/ops/S16_PLAN.md（S16-00..03固定、S16-02/03の目的追記）
- [x] Update: docs/ops/S16_TASK.md（S16全体の実行順序の固定）

## Gate (MUST)
- [x] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'`
- [x] `bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'`

## Policy Scan (MUST)
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; set -u; PAT="$(printf "%c%c%c%c%c%c%c" 102 105 108 101 58 47 47)"; git grep -n -F -- "$PAT"; st=$?; case "$st" in 0) echo "[FAIL] forbidden file URL found" >&2; exit 1 ;; 1) echo "[OK] none" ;; *) echo "[ERROR] git grep failed (exit=$st)" >&2; exit "$st" ;; esac'`

## Commit
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git add docs/ops/S16-02_PLAN.md docs/ops/S16-02_TASK.md docs/ops/S16_PLAN.md docs/ops/S16_TASK.md'`
- [x] `bash -lc 'cd "$(git rev-parse --show-toplevel)"; git commit -m "chore(docs): standardize repo-absolute plan/task (S16-02)"'`
