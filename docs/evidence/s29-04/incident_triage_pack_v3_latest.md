# S29-04 Incident Triage Pack v3 (Latest)

- CapturedAtUTC: `2026-02-27T11:07:47Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `4d5916728a1831687c05062a875520825c77e1db`

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
