# CI Required Checks

This document defines the required GitHub Actions checks for maintaining code quality and stability.

## Required Checks List

The following checks must pass for any Pull Request targeting `main`.

| Check Name (Context) | Workflow | Trigger | Description |
| :--- | :--- | :--- | :--- |
| **test** | Test | `pull_request` | Runs `make test` (Go + Python unit tests). |
| **verify-pack** | Verify Pack | `pull_request` | Runs full pack verification for impact changes; docs-only changes run a lightweight mode while keeping the required check context. |

Note: `milestone_required` exists as a detection check but is NOT required by default (policy decision later).

## Optional / Aggregator Checks

- **Lint Go**: Optional by default.
- **Lint Markdown**: Optional by default.
- **summary**: A job in `CI (Lint & Verify)` that aggregates lint results.
  - *Status*: Recommended as Optional (Informational).
  - Can be made required if strict "all lints pass" enforcement is desired via a single status check.

## Enforcement

- These checks are configured in GitHub repository settings under **Branches** -> **Branch protection rules** -> **main**.
- **Require status checks to pass before merging** should be enabled with the list above.

<!-- required_checks_sot:v1
# auto-managed. run: bash ops/required_checks_sot.sh write-sot
# NOTE: empty/missing live required checks => ERROR (fail-closed)
test
verify-pack
-->
