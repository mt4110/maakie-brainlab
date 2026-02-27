# S18-01 TASK — Phase Scaffold Generator v1

## Scope Lock
- Implement ONLY: ops/new_ops_phase.sh (v1 minimal)
- No extra flags/features
- No canonical updates

## Checklist (Order is Deterministic)

### Phase 0 — Snapshot
- [x] cd repo root
- [x] confirm branch = s18-01-phase-scaffold-v1
- [x] git status clean enough to proceed

### Phase 1 — Docs Permission (Start Allowed)
- [x] docs/ops/S18_PLAN.md contains S18-01 entry (scope pinned)
- [x] docs/ops/S18_TASK.md optionally points to generator usage

### Phase 2 — Implement Generator (ops/new_ops_phase.sh)
- [x] create ops/ directory if missing
- [x] write ops/new_ops_phase.sh
- [x] chmod +x ops/new_ops_phase.sh
- [x] shellcheck is optional (no new gate)

### Phase 3 — Smoke Test (No permanent pollution)
- [x] run: ops/new_ops_phase.sh S18-99 "Smoke Phase"
- [x] confirm files created
- [x] run again: confirm SKIP lines and no overwrite
- [x] cleanup: git restore created smoke files (or remove) so they don't ship

### Phase 4 — Gates
- [x] make test
- [x] go run cmd/reviewpack/main.go submit --mode verify-only

### Phase 5 — Commit / PR
- [x] git add -A
- [x] git commit -m "chore(ops): add phase scaffold generator v1 (S18-01)"
- [x] git push -u origin HEAD
- [x] gh pr create --fill
