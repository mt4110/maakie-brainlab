# ops/ci

This directory contains scripts and configuration for CI workflows.

## Scripts

- `verify_pack_ci.sh`: Main entry point for CI pack verification (legacy path).
- `decide_cost_scope.py`: Decides whether `verify_pack` should run heavy steps.

## Config

- `cost_scope_policy.json`: Source of truth for CI cost mode behavior.
  - `default_mode`: `balanced`
  - `modes` enum: `lite`, `balanced`, `full`
  - `docs_only_allowlist_globs`: patterns allowed for docs-only lightweight runs

## Usage

The scripts are designed to be run by GitHub Actions (`.github/workflows/verify_pack.yml`) and can also be tested locally.

Example:

```bash
python3 ops/ci/decide_cost_scope.py \
  --policy ops/ci/cost_scope_policy.json \
  --event pull_request \
  --ref refs/pull/1/merge \
  --mode balanced \
  --changed-file docs/ops/README.md \
  --json
```
