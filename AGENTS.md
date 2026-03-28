# AGENTS.md — Ritual 22-16-22-99 (Minimal)

## Non-negotiables
- Use Ritual `22-16-22-99` as the default workflow.
- Keep milestone checks non-blocking. Do not introduce milestone-required gates.
- Do not use `STATUS.md` as a progress source of truth. Put progress in PR body.
- Before PR creation/update, run ci-self gate and proceed only when checks are all green (adapting paths to your local setup):
  - `source /path/to/your/nix/profile.d/nix-daemon.sh`
  - `cd $REPO_ROOT`  <!-- $REPO_ROOT: root of this repository -->
  - `ci-self up --ref "$(git branch --show-current)"`

## Branch Rule (Problem Pattern Limited)
- Forbidden branch pattern: `codex/feat*` only.
- If a forbidden branch is detected, do not continue implementation on that branch.
- Recovery rule (mandatory):
  - Create a new compliant branch from the same `HEAD`.
  - Continue work on the new branch.
  - Example:
    - `git switch -c feat/<slug>`
    - `git branch -D codex/feat-...` (optional cleanup after switching)

## Ritual Trigger
- If user prompt contains `22-16-22-99`, run:
  - PLAN: acceptance criteria + impacted files
  - DO: minimal implementation
  - CHECK: run standard checks
  - SHIP: commit + PR body (include test commands and results)

## Product source of truth

- Before implementation, read `PRODUCT.md`.
- For product scope, UX, navigation, and feature priority, `PRODUCT.md` wins over existing UI, README, and legacy surface behavior.
- `AGENTS.md` governs workflow, checks, and branch rules.
- `PRODUCT.md` governs what to build and what to remove.
- During migration, do not treat current dashboard surface as the target UX.