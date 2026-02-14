# S15-07..10 Dependency & TouchSet Matrix

## Evidence (discovery commands)
- ls -la docs/ops | rg "S15[-_](07|08|09|10)"
- rg "S15[-_](07|08|09|10)" docs/ops/S15_PLAN.md docs/ops/S15_TASK.md
- rg "S15[-_](07|08|09|10)" docs/ops -S

## Matrix

| Step | Title | Depends On | TouchSet (planned) | Overlap Risk | PR Unit | Gate |
|------|-------|------------|--------------------|--------------|---------|------|
| 07   | Design Kickoff | None | docs/ops/S15_07* | No | 1 PR | docs-only |
| 08   | Impl Split | 07 | docs/ops/S15_08*, MATRIX | No | 1 PR | docs-only |
| 09   | Impl Part A | 08 | internal/reviewpack/submit.go | No | 1 PR | code-change |
| 10   | Impl Part B | 09 | internal/reviewpack/verify.go | No | 1 PR | code-change |

## Dependency Edges
- 07 -> (kickoff)
- 08 -> 07 (doc dependency)
- 09 -> 08 (rule lock dependency)
- 10 -> 09 (serial implementation)

## TouchSet Overlap (Lock)
- 07 vs 08: docs/ops prefix (isolation by suffix)
- 08 vs 09: 08 locks the rules for 09
- 09 vs 10: Pending (Locked in 09 kickoff)

## Implementation PR Split Decision (Mechanical)
Decision: 1 PR per step

Rule:
- If any dependency edge exists OR any TouchSet overlap => 1 PR per step
- Else => allow 07+08 and 09+10 bundling

> [!IMPORTANT]
> S15-08 locks these rules. S15-09/10 TouchSets will be refined but must honor the serial dependency (09 then 10).
