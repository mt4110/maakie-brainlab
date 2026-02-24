# S22-10_PLAN — Public Hardening v1 (release hygiene + threat model + injection sim)
Last Updated: 2026-02-24

## Principles (Non-Negotiable)
- stopless: **NO exit / NO return non-zero / NO set -e / NO trap EXIT**
- Python: **NO sys.exit / NO SystemExit / NO assert**
- Failure handling: print **OK/ERROR/SKIP**, keep going only when safe
- Heavy work: split steps, timebox by design (small runs), avoid CPU spikes

## GOAL
Long-term outer wall for public durability:
- Minimal `SECURITY.md`
- `docs/ops/THREAT_MODEL_v1.md` (attack surface enumeration + mitigations)
- `docs/ops/INJECTION_SIM_SUITE_v1.md` (attack case catalog, 5–10 cases)
- `tests/test_injection_sim_smoke.py` (light smoke to prevent silent regression)

## STATE
STOP = 0
ROOT = repo root
OBS  = .local/obs/s22-10_<UTC>
BR   = s22-10-public-hardening-threat-injection-v1

## A) Kickoff / Ledger
if ROOT missing:
  print ERROR; STOP=1
else:
  sync main (fetch/prune, switch main, pull --ff-only)
  switch/create BR
  ensure files exist:
    - docs/ops/S22-10_PLAN.md
    - docs/ops/S22-10_TASK.md
  update SOT:
    - docs/ops/STATUS.md: set S22-10 to "1% (WIP)" (idempotent)
  note: untracked files must be quarantined into .local/tmp to avoid PR contamination

## B) SECURITY.md (minimal)
create root SECURITY.md
constraints:
  - no secrets
  - no absolute local paths
  - simple reporting & supported versions

## C) THREAT_MODEL_v1
create docs/ops/THREAT_MODEL_v1.md
include:
  - assets to protect (evidence, bundles, IL runs, CI trust)
  - attacker model & capabilities
  - attack surfaces (path traversal, injection, timestamp contamination, tar canonicalization bypass, supply chain)
  - mitigations & detection artifacts (what logs / what gates)
  - residual risk (known limitations)

## D) INJECTION_SIM_SUITE_v1
create docs/ops/INJECTION_SIM_SUITE_v1.md
rules:
  - start with 5–10 major cases
  - each case must include: id, category, target surface, vector, expected behavior (OK/ERROR/SKIP), notes
  - fixture is optional; if present, must be relative path only

## E) Smoke test (light)
create tests/test_injection_sim_smoke.py
constraints:
  - no sys.exit / SystemExit / assert
  - do not raise exceptions to stop the process
behavior:
  - load suite doc
  - parse cases; if fixtures exist:
      - verify file exists
      - if json/jsonl: verify parseability (light)
  - print OK/ERROR/SKIP lines
  - always end without terminating the process

## F) Verification (light / split)
Step F1: run smoke only
Step F2: run existing checks only if CPU safe for the moment (split if needed)
Always store logs under OBS

## G) Commit + PR
commit docs/tests changes
PR:
  - milestone: S22-10
  - include verify-only bundle sha in body
merge:
  - must use ops/pr_merge_guard.sh (merge-commit)

## CLOSEOUT (after merge)
update docs/ops/STATUS.md:
  - S22-10: 100% (Merged PR #??)
close milestone S22-10 (if appropriate)
