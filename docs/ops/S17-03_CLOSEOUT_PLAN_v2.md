# S17-03 Closeout Plan v2 (Hygiene Capsule)

## Invariants (MUST)
- Tracked files must NOT contain the forbidden token: `file` + `://` (concatenated form).
- Docs must never embed the forbidden token literally.
  - Real URI => `[FILE_URI]`
  - Pattern mention => `file:/{2}` (regex notation)

## P0: Safety Snapshot
- require `git status -sb` clean OR commit first

## P1: Hygiene Capsule (terminal-only check, but safe to paste here)
- FORBID := "$(printf '%s%s' 'file' '://')"
- if rg(FORBID, docs, ops, .github, internal) hits > 0:
    - run: `bash ops/finalize_clean.sh --fix`
    - stage updated files
    - re-run rg(FORBID, ...) until hits == 0
  else:
    - continue

## P2: Canonical Capsule
- Canonical values live ONLY in PR body.
- Tracked docs must point to PR body and must not contain canonical tuple literals.

## P3: Gates
- make test
- reviewpack submit --mode verify-only

## Stop Conditions
- any hygiene hit => ERROR (fix before proceeding)
- any contradiction (tracked docs contain canonical tuple literals) => ERROR
