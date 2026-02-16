# S18-01 TASK — Phase Scaffold Generator v1

## Scope Lock
- Implement ONLY: ops/new_ops_phase.sh (v1 minimal)
- No extra flags/features
- No canonical updates

## Checklist (Order is Deterministic)

### Phase 0 — Snapshot
- [ ] cd repo root
- [ ] confirm branch = s18-01-phase-scaffold-v1
- [ ] git status clean enough to proceed

### Phase 1 — Docs Permission (Start Allowed)
- [ ] docs/ops/S18_PLAN.md contains S18-01 entry (scope pinned)
- [ ] docs/ops/S18_TASK.md optionally points to generator usage

### Phase 2 — Implement Generator (ops/new_ops_phase.sh)
- [ ] create ops/ directory if missing
- [ ] write ops/new_ops_phase.sh
- [ ] chmod +x ops/new_ops_phase.sh
- [ ] shellcheck is optional (no new gate)

### Phase 3 — Smoke Test (No permanent pollution)
- [ ] run: ops/new_ops_phase.sh S18-99 "Smoke Phase"
- [ ] confirm files created
- [ ] run again: confirm SKIP lines and no overwrite
- [ ] cleanup: git restore created smoke files (or remove) so they don't ship

### Phase 4 — Gates
- [ ] make test
- [ ] go run cmd/reviewpack/main.go submit --mode verify-only

### Phase 5 — Commit / PR
- [ ] git add -A
- [ ] git commit -m "chore(ops): add phase scaffold generator v1 (S18-01)"
- [ ] git push -u origin HEAD
- [ ] gh pr create --fill
