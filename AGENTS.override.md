# AGENTS.override.md

## Branch-local override

This branch is no longer optimizing the public Q&A path as its main battlefield.

- Keep `PRODUCT.md` as the public product definition for the legacy/public track.
- For implementation choices on this branch, prefer `IL_PIVOT_PRODUCT.md` as the research north star.
- Keep Ritual `22-16-22-99` as the default workflow.
- Do not treat `STATUS.md` as a source of truth. Put progress in the PR body.
- Keep milestone checks non-blocking.
- Before PR creation or update, run the `ci-self` gate from the repository root and proceed only when it is green.
- Keep the forbidden branch rule from `AGENTS.md`: do not continue on `codex/feat*`.

## Active instruction summary

- Do not spend the main effort on polishing `/`, `/questions`, or `/evidence` for public end-user Q&A.
- Keep legacy public surfaces stable, but treat them as maintenance-only in this branch.
- Reuse the existing dashboard as an operator/research cockpit under `/ops`.
- Prefer deterministic state, typed blocked reasons, evidence linkage, and pause/resume over flashy orchestration.
- Reuse existing IL, evidence, reviewpack, and dashboard assets where possible.
- Do not build crawler infrastructure in this branch.
- Do not introduce a new public-facing product surface; the new work stays under operator/research routes.

## Working rule for this branch

When `PRODUCT.md` and the new research cockpit direction disagree, keep the public track stable and prefer `IL_PIVOT_PRODUCT.md` for branch-local implementation decisions.
