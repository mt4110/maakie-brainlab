# S30-1-S30-900 THREAD v1 PLAN - Experience-first Backlog Burn

Last Updated: 2026-02-27

## Goal

- Reclassify the pending ~900 checkbox backlog by impact on day-to-day usability, not by raw count.
- Burn down in this order:
  1. Daily flow failure-point elimination (`execute -> verify -> judge`)
  2. Log/output clarity ("see and understand immediately")
  3. Automation of repetitive operation
- Lock a deterministic full-queue execution order until pending tasks become zero.

## Current Point (2026-02-27)

- Branch: `ops/S30-1-S30-900`
- Backlog source: pending checkboxes in `docs/ops/**/*.md`, `docs/rules/**/*.md`, `docs/pr_templates/**/*.md`, and `+PTASK+`
- Reclassification artifact: `docs/evidence/s30-01/task_reclass_latest.json`
- Execution policy: process the ranked queue to completion (`pending_total=0`).

## Non-negotiables

- Ritual `22-16-22-99` is the default workflow (`PLAN -> DO -> CHECK -> SHIP`).
- Milestone checks remain non-blocking; do not add milestone-required gates.
- Do not use `docs/ops/STATUS.md` as progress SOT (use TASK + PR body).
- Before PR create/update, run:
  - `source /path/to/your/nix/profile.d/nix-daemon.sh`
  - `ci-self up --ref "$(git branch --show-current)"`
- Forbidden branch pattern `codex/feat*` must not be used.

## Experience Axes

### Axis A: Flow Failzero (highest priority)

- Focus: eliminate breakpoints in daily operation (`run`, `verify`, `judge`).
- Typical signals: `verify`, `test`, `gate`, `readiness`, `ERROR/FAIL/STOP`.

### Axis B: Log Clarity

- Focus: normalize logs and outputs into instantly readable, decision-ready shape.
- Typical signals: `log`, `output`, `OBS`, `summary`, `artifact`, `OK/WARN/ERROR/SKIP`.

### Axis C: Automation

- Focus: remove repeated manual operations via scripts/workflows/templates.
- Typical signals: `script`, `workflow`, `make`, `template`, `loop`, `batch`, `rerun`.

## Completion Definition (v1 Exit)

- `scripts/ops/s30_task_reclassify.py` deterministically produces ranked backlog artifacts.
- `docs/evidence/s30-01/task_reclass_latest.{json,md}` are current and committed.
- Full backlog completion is recorded in artifact order and reflected in TASK + commit log.
- `scripts/ops/current_point.py` resolves `S30-1-S30-900` branch naming.

## Delivery Phases

1. Phase-1 Design Freeze
   - Fix axis definitions, ranking contract, output schema, and thread-switch rule.
2. Phase-2 Big Commit Batch
   - Apply script + docs + roadmap updates in one cohesive change.
3. Phase-3 Operational Burn
   - Execute ranked queue to completion and update artifacts (`pending_total=0`).
4. Phase-4 Ship Gate
   - Run `make verify-il`; run `ci-self` best-effort when remote ref exists.

## Planned Impacted Files

- `scripts/ops/s30_task_reclassify.py`
- `scripts/ops/current_point.py`
- `tests/test_s30_task_reclassify.py`
- `tests/test_current_point.py`
- `Makefile`
- `docs/ops/S30-1-S30-900-THREAD-V1_PLAN.md`
- `docs/ops/S30-1-S30-900-THREAD-V1_TASK.md`
- `docs/ops/ROADMAP.md`
- `docs/evidence/s30-01/task_reclass_latest.json`
- `docs/evidence/s30-01/task_reclass_latest.md`

## Validation Strategy

Light:
- `make ops-now`
- `make s30-task-reclassify`
- `python3 -m unittest -v tests/test_current_point.py tests/test_s30_task_reclassify.py`

Ship:
- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"` (best-effort under commit-only/no-push policy)
