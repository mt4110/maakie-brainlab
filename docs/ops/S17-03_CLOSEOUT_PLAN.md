# PLAN: S17-03 Closeout (Stop Infinite Drift)

## P0: Snapshot
- repo_root := `cd "$(git rev-parse --show-toplevel)"`
- branch := `git rev-parse --abbrev-ref HEAD`
- if branch == "main": error("do not operate on main")
- require `git status -sb` clean OR commit first

## P1: Hygiene invariant
- if `rg('file://', docs, ops, .github, internal)` hits > 0:
    - error("forbidden file:// exists; must obfuscate/remove")

## P2: Canonical must live ONLY in PR body
- deny := [chosen canonical commit/bundle/sha OR legacy canonical tokens]
- if any deny tokens appear in repo tracked docs (outside allowed historical raw logs):
    - error("canonical leaked into repo; must be PR-body-only to stop drift")

## P3: PR body is the only canonical
- Update PR #51 body “Canonical Ritual” block to chosen canonical tuple
- Ensure tracked docs say: “Canonical: see PR #51 body” (no literal values)

## P4: Gates
- Run `make test`
- Run `go run cmd/reviewpack/main.go submit --mode verify-only`
- Note: output bundle/sha are Observation (do not update Canonical)

## P5: Done
- if all PASS: mark DONE, merge-ready
- else: error("closeout blocked")
