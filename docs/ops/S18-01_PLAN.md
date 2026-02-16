# S18-01 PLAN — Phase Scaffold Generator v1

## Status
- Phase: S18-01
- Canonical: NO UPDATE (this phase only produces Observation bundles)

## Goal
TBDを消す。次フェーズの PLAN/TASK を決定論で安全生成できる「道具」を1つ実装し、以後の ops フェーズ開始を止めない。

## Scope Lock (NO LATE CHANGES)
This phase includes ONLY:
- Implement: ops/new_ops_phase.sh
- Inputs: <PHASE_ID> <TITLE>
- Outputs:
  - docs/ops/${PHASE_ID}_PLAN.md
  - docs/ops/${PHASE_ID}_TASK.md
- Template sources (pinned):
  - docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md
  - docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md
- Rules:
  - No overwrite: if output exists -> SKIP with 1-line reason, exit 0
  - No `set -e` / no strictmode that drops terminal
  - Deterministic header: `# ${PHASE_ID} PLAN — ${TITLE}` / `# ${PHASE_ID} TASK — ${TITLE}`
  - Avoid duplicate top-level heading from template: drop first `# ...` line if present
  - Errors are explicit: print 1-line `ERROR:` and exit non-zero

Non-goals:
- No canonical pin update
- No retroactive edits to S17 / S18-00
- No multi-epic automation beyond simple PHASE_ID file generation
- No extra flags (dry-run等) 追加しない（v1は最小）

## Deliverables
- ops/new_ops_phase.sh
- docs/ops/S18-01_PLAN.md (this)
- docs/ops/S18-01_TASK.md
- docs/ops/S18_PLAN.md updated (S18-01 row and start permission)
- docs/ops/S18_TASK.md updated (optional pointer to generator)

## Acceptance
- Running:
  - `ops/new_ops_phase.sh S18-99 "Smoke Phase"`
  creates (if missing):
  - docs/ops/S18-99_PLAN.md
  - docs/ops/S18-99_TASK.md
  and never overwrites existing files.
- Gates:
  - make test PASS
  - reviewpack submit --mode verify-only PASS

## Risks / Mitigations
- macOS tool differences: use POSIX-ish bash + awk, avoid GNU-only options.
- Accidental overwrite: explicit existence checks + SKIP.

## Implementation Outline (Pseudo-code)
try:
  if args missing -> error usage
  resolve repo root via `git rev-parse --show-toplevel` else error
  verify template files exist else error

  for each output in [PLAN, TASK]:
    if file exists:
      print "SKIP: exists <path>"
      continue
    else:
      write temp file:
        print deterministic header
        print blank line + generator note
        append template body, but if first line is '# ' heading -> drop it
      atomic move temp -> target
      print "OK: wrote <path>"

catch error:
  print "ERROR: <reason>"
  exit non-zero
