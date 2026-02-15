# PLAN: S17-03 FINALIZE Canonical Audit
Status: IN_PROGRESS
Owner: ambi
Progress: 0%

## Goal
- Resolve infinite drift by pinning the canonical reference to the latest commit `0310890` and bundle `135256`.
- Close PR #51 with zero contradictions.

## Canonical Definition (Single Source of Truth)
- Commit: `03108902475ec622596da49e060422e285ae4564`
- Bundle: `review_bundle_20260215_135256.tar.gz`
- SHA256: `7f444f689d06e2acd830c4cbafc17f26a111ff0c1616b5df6580f096bedd2587`
- **History**: `03cc...` / `121251` is demoted to HISTORIAL/REFERENCE status.

## Invariants
- `docs/ops/S17-03_TASK.md` uses CANONICAL.
- `docs/evidence/s17-03/fix_summary.md` uses CANONICAL.
- `docs/evidence/s17-03/fix_evidence.txt` uses CANONICAL.
- `file://` count in repo is 0.
- `run_always_1h.yml` uses materialized secrets for signing.

## Plan Pseudocode
1. **Safety Snapshot**: Ensure we are on commit `0310890`.
2. **Canonical Replacement**: Replace all `03cc...` with `7f444f...` (except in historical sections).
3. **Guard**: Verify CI workflow logic (`secrets.S6_SIGNING_KEY_B64`).
4. **Gate**: Run `make test` and `verify-only`.
5. **Stop Condition**: Any `file://` remaining or canonical mismatch -> ERROR.
