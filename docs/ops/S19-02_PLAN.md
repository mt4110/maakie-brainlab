# S19-02: prbodyfix (Go Single impl / CI+Local unified)

## Goal
Unify PR body sentinel/empty cleaning logic into a single Go implementation (`internal/prbodyfix`) used by both CI and generic local tools.
Replace the existing JS-based `github-script` in `.github/workflows/pr_body_required.yml` with a Go tool `cmd/prbodyfix`.
Retire the duplicate logic in `cmd/prkit` (if any) or align it to use `internal/prbodyfix`.

## Current Spec (Truth)
Currently defined in `.github/workflows/pr_body_required.yml`:
- Sentinel: `PR_BODY_TEMPLATE_v1:`
- Logic:
    1. Split by line.
    2. Trim each line.
    3. If `strings.TrimSpace(line)` starts with sentinel, drop the line.
    4. Join with `\n`.
    5. Trim result (start/end).
    6. If empty, fetch template (from base), clean template, use that.
    7. Ensure single trailing newline.

## Architecture
- **Lib**: `internal/prbodyfix` (Pure logic: Normalize, Clean)
- **CI Tool**: `cmd/prbodyfix` (GitHub Actions integration: Reads `GITHUB_EVENT_PATH`, calls Lib, updates PR via API)
- **Local Tool**: `cmd/prkit` (or similar) will use `internal/prbodyfix` to ensure localized behavior matches CI.

## Files
- `internal/prbodyfix/prbodyfix.go`: Core logic.
- `internal/prbodyfix/prbodyfix_test.go`: Tests covering spec.
- `cmd/prbodyfix/main.go`: CI entrypoint.
- `.github/workflows/pr_body_required.yml`: Updated workflow.

## Verification
- `go test ./internal/prbodyfix/...`
- CI dry-run (initially) or verify via `reviewpack submit --mode verify-only` locally.
