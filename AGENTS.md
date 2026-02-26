# AGENTS.md — Ritual 22-16-22-99 (Minimal)

## Non-negotiables
- Use Ritual `22-16-22-99` as the default workflow.
- Keep milestone checks non-blocking. Do not introduce milestone-required gates.
- Do not use `STATUS.md` as a progress source of truth. Put progress in PR body.
- Before PR creation/update, run ci-self gate and proceed only when checks are all green:
  - `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
  - `cd ~/dev/maakie-brainlab`
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
