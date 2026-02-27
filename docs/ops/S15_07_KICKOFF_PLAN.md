# S15-07 kickoff (07-10 design freeze)

## Goal
- Freeze S15-07..10 design in docs:
  - PLAN/TASK for each step
  - dependency + TouchSet matrix
  - mechanical rule for PR splitting (1-by-1 vs 2-bundle)

## Non-Goals
- No implementation changes in this PR (docs-only)
- No refactors outside docs alignment

## Inputs (Source of Truth)
- docs/ops/S15_PLAN.md
- docs/ops/S15_TASK.md
- Existing docs/ops/S15_07..10 artifacts if present

## Output Artifacts
- docs/ops/S15_07_KICKOFF_PLAN.md (this)
- docs/ops/S15_07_KICKOFF_TASK.md
- docs/ops/S15_07_10_DEPENDENCY_MATRIX.md
- docs/ops/S15_07..10 PLAN/TASK (normalized)

## Pseudocode (Phases)

PHASE 0: Preflight
  - Confirm clean working tree
  - Record baseline: HEAD sha, date, branch name

PHASE 1: Discover existing S15-07..10 docs
  - Enumerate docs/ops for S15-07..10 (name variants)
  - Extract titles/intent lines from S15_PLAN.md / S15_TASK.md

PHASE 2: Normalize naming + structure
  - For each step (07..10):
      IF plan/task files exist:
          - align headers/sections to template
      ELSE:
          - create new plan/task using template
  - Update S15_PLAN.md / S15_TASK.md references if needed (only minimal)

PHASE 3: Fill TouchSet + Dependencies
  - For each step plan:
      - TouchSet: list directories/files intended to change (placeholder allowed, but must be explicit)
      - Dependencies: explicit "Depends on S15-0X" or "None"

PHASE 4: Build Dependency Matrix
  - Create docs/ops/S15_07_10_DEPENDENCY_MATRIX.md
  - Decide implementation PR split mechanically:
      IF any dependency edge exists OR any TouchSet overlaps:
          decision = "1 PR per step"
      ELSE:
          decision = "allow 07+08 and 09+10 bundling"

PHASE 5: Consistency check (docs integrity)
  - rg for broken references / missing step IDs
  - Ensure all referenced files exist

PHASE 6: Commit + Push + PR
  - Single docs-only PR
  - Evidence: command outputs recorded in PR body or in matrix
