# IL_PIVOT_PRODUCT.md

## 0. Role

This document is the branch-local research north star for the IL / semi-autonomous pivot.

Decision priority on this branch:

1. `IL_PIVOT_PRODUCT.md`
2. `AGENTS.override.md`
3. `AGENTS.md`
4. `PRODUCT.md`
5. existing dashboard surfaces and implementation details

`PRODUCT.md` still defines the legacy/public track. This file defines what this branch is trying to make true.

## 1. One sentence

maakie-brainlab on this branch is an IL / semi-autonomous research cockpit for turning natural-language goals into structured plans, step execution, evidence, artifacts, and next actions.

## 2. Primary goal

Turn a natural-language objective into:

- a normalized objective
- an IL plan
- an approval step
- resumable step execution
- evidence and artifacts per step
- an interim or final result
- a typed blocked reason and next action when progress stops

## 3. Not the goal

- public Q&A path polishing
- end-user redesign of `/documents`, `/questions`, or `/evidence`
- a generic autonomous-agent platform
- crawler implementation itself
- web-scale ingestion
- flashy autonomy without replayable state

## 4. North star loop

Goal -> Normalize -> IL Plan -> Approve -> Execute -> Evidence -> Artifact -> Next Action -> Resume

## 5. V0 scope

V0 is one workflow only: `repo/docs research workflow`.

Representative goals:

1. detect internal route leaks from the repo main path and emit a correction plan
2. extract API contracts and constraints from imported docs
3. identify contradictions across `PRODUCT.md`, `README.md`, and `AGENTS.md`
4. summarize important requirements from imported docs
5. create a reviewpack-style artifact from repo/docs evidence

## 6. Core contracts

### Input

- `GoalInput`

### Internal state

- `NormalizedObjective`
- `ILPlan`
- `ILStep`
- `RunState`
- `StepResult`
- `EvidenceItem`
- `ArtifactRef`
- `BlockedReason`
- `NextAction`

### Output

- plan preview
- step execution timeline
- evidence list
- artifacts
- interim/final result
- next action
- blocked reason

## 7. Minimum step kinds

- `search_local_corpus`
- `inspect_repo_or_docs`
- `extract_candidates`
- `synthesize_result`
- `request_human_input`
- `emit_artifact`

## 8. Operator UX

The research surface lives under `/ops/agent`.

Required screens:

- `/ops/agent`: new goal input, recent runs, status counts, resume entry
- `/ops/agent/[id]`: plan, steps, evidence, artifacts, result, blocked reason, next action

This is an operator/research cockpit, not a public-facing product surface.

## 9. Minimal architecture

### Runtime

- compile a goal into deterministic structured data
- persist run state and step state
- execute one step at a time
- distinguish `queued`, `running`, `blocked`, `done`, and `failed`
- allow approve, retry, pause, and resume

### Persistence

- store runs, steps, evidence, artifacts, and run summaries in local durable storage
- keep data replayable and resumable
- attach evidence and artifacts to step ids and run ids

### Dashboard

- show plan before execution
- show current step progression
- surface blocked reason with a typed code and human-readable guidance
- show next action as one sentence

## 10. Reuse strategy

Reuse these assets when possible:

- `ops/dashboard` route shell and `/ops` information architecture
- existing server-side data access patterns
- existing SQLite-backed persistence patterns
- existing evidence/reviewpack/export artifacts
- existing IL compile/execute assets where they already fit the V0 workflow

Do not restart public main-path polishing in this branch.

## 11. Success metrics

- representative goal completion rate
- evidence attachment rate
- blocked reason typing rate
- resume success rate
- median manual interventions per run

## 12. Done for this PR

This PR is done when:

- one natural-language goal can be entered
- a plan preview is shown
- approval starts execution
- each step has a persisted status
- evidence and artifacts are attached to steps
- blocked runs stop with a typed reason
- a blocked run can be resumed
- an interim or final result and next action are visible
