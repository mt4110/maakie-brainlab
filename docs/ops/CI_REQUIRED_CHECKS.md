# CI Required Checks

This document defines the required GitHub Actions checks for maintaining code quality and stability.

## Required Checks List

The following checks must pass for any Pull Request targeting `main`.

| Check Name (Context) | Workflow | Trigger | Description |
| :--- | :--- | :--- | :--- |
| **Lint Go** | CI (Lint & Verify) | `pull_request` | Validates Go code using `golangci-lint`. |
| **Lint Markdown** | CI (Lint & Verify) | `pull_request` | Validates Markdown files using `markdownlint-cli2`. |
| **test** | Test | `pull_request` | Runs `make test` (Go + Python unit tests). |
| **verify-pack** | Verify Pack | `pull_request` | Ensures `review_pack` generation works and output is clean. |

## Optional / Aggregator Checks

- **summary**: A job in `CI (Lint & Verify)` that aggregates lint results.
    - *Status*: Recommended as Optional (Informational).
    - Can be made required if strict "all lints pass" enforcement is desired via a single status check.

## Enforcement

- These checks are configured in GitHub repository settings under **Branches** -> **Branch protection rules** -> **main**.
- **Require status checks to pass before merging** should be enabled with the list above.
