# Lint Ramp-Up Plan

This document outlines the strategy for elevating lint rules from advisories to blocking requirements.

## Ramp-Up Stages

1.  **Warning (Advisory)**
    *   New linters are added with `continue-on-error: true`.
    *   Developers can see feedback but merging is not blocked.
    *   *Status*: **Active** for new experimental linters.

2.  **New-Only (PR Blocking)**
    *   Lints are enforced on **new code only** (modified lines in PR).
    *   Prevents regression ("stop the bleeding") without requiring a massive cleanup of legacy code.
    *   *Status*: **Active** for `golangci-lint` (via `new-from-rev`).

3.  **Config Validation (Strict)**
    *   Configuration errors (e.g., invalid `.golangci.yml` or `.markdownlint.json`) must always fail the build immediately.
    *   Ensures the linting toolchain is actually running.
    *   *Status*: **Active**.

4.  **Critical Rules (Strict)**
    *   Specific, high-value rules (e.g., security checks, major bugs) are enforced on the **entire codebase**.
    *   Legacy violations must be fixed or explicitly ignored.

5.  **Strict (Full Enforcement)**
    *   All enabled linters must pass on the entire codebase.
    *   `continue-on-error: false`.
    *   *Goal*: Final state for mature projects.
