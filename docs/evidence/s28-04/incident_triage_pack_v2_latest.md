# S28-04 Incident Triage Pack v2 (Latest)

- CapturedAtUTC: `2026-02-27T07:07:33Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `81102446eb5a9f461a4baf4b243286fc004d9ed4`

## Summary

- status: `WARN`
- reason_code: `TRIAGE_ALERT`
- missing_inputs: `0`
- alerts: `4`

## Top Reasons

- MISSING_PROVIDER_ENV: `1`
- NOTIFY_DRY_RUN: `1`
- RECOVERY_REQUIRED: `1`
- SKIP_RATE_HIGH: `1`

## Priority Actions

- Validate provider env variables and credentials wiring.
- Run strict canary once and verify status transition to PASS.
- Collect at least 2 additional labeled cases for taxonomy 'provider'.
- Collect at least 1 additional labeled cases for taxonomy 'network'.
- Configure readiness webhook and re-run notification dispatch.
