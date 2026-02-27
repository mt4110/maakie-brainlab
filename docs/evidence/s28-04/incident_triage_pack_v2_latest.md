# S28-04 Incident Triage Pack v2 (Latest)

- CapturedAtUTC: `2026-02-27T07:32:34Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `fa136531e69807a535ac6f51146fdfbead621a06`

## Summary

- status: `WARN`
- reason_code: `TRIAGE_ALERT`
- missing_inputs: `0`
- alerts: `5`

## Top Reasons

- MISSING_PROVIDER_ENV: `1`
- NOTIFY_DRY_RUN: `1`
- RECOVERY_REQUIRED: `1`
- SKIP_RATE_HIGH: `1`
- UNKNOWN_RATIO_ABOVE_TARGET: `1`

## Priority Actions

- Validate provider env variables (`base_url/api_key/model`) in runtime and CI contexts.
- Run strict canary once and verify status transition to PASS after recovery action.
- Keep rollback path ready: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
- Collect at least 2 additional labeled cases for taxonomy 'provider'.
- Collect at least 1 additional labeled cases for taxonomy 'network'.
- Collect at least 1 additional labeled cases for taxonomy 'schema'.
- Configure readiness webhook and enable re-delivery with retries.
- Resolve notification issue: NOTIFY_DRY_RUN.
