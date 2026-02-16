# S18-02 TASK — Hardening (truthful write + PHASE_ID sanitize)

## Checklist (order is binding)

- [ ] 0) Preflight snapshot (git status / branch)
- [ ] 1) Scope Lock confirmed in PLAN/TASK (this file + PLAN)
- [ ] 2) Update epic start permission lines (S18_PLAN / S18_TASK) (skip if already present)
- [ ] 3) Patch `ops/new_ops_phase.sh` (sanitize + truthful write) with minimal diff
- [ ] 4) Smoke: reject bad PHASE_ID (must fail, must not print OK)
- [ ] 5) Smoke: accept good PHASE_ID (create files), then cleanup (rm)
- [ ] 6) Gates: make test
- [ ] 7) Gates: reviewpack submit --mode verify-only
- [ ] 8) Commit / Push / PR

## Commands (small + IF/ELSE style)

### 0) Preflight snapshot
cd "$(git rev-parse --show-toplevel)"
git status -sb
git rev-parse --abbrev-ref HEAD

### 1) Epic start permission lines (skip if already present)
cd "$(git rev-parse --show-toplevel)"
rg -n "S18-02" docs/ops/S18_PLAN.md && echo "SKIP: S18-02 already in S18_PLAN.md" || \
cat >> docs/ops/S18_PLAN.md <<'EOF'

- S18-02: Hardening — new_ops_phase.sh truthful write + PHASE_ID sanitize (scope pinned; implementation allowed)
