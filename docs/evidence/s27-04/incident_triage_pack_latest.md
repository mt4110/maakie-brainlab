# S27-04 Incident Triage Pack (Latest)

- CapturedAtUTC: `2026-02-27T04:16:28Z`
- Branch: `ops/S27-01-S27-10`
- HeadSHA: `02f0f008326b975d7100e79201a4370e4f5c81aa`

## Summary

- status: `WARN`
- reason_code: `TRIAGE_ALERT`
- missing_inputs: `0`
- alerts: `2`

## Top Reasons

- MISSING_PROVIDER_ENV: `1`
- SKIP_RATE_HIGH: `1`

## Rollback

- command: `python3 scripts/ops/s25_langchain_poc.py --mode rollback-only`

## PR Body Snippet

```md
### S27-04 Incident Triage Pack
- status: WARN
- reason_code: TRIAGE_ALERT
- top_reasons: [{'reason_code': 'MISSING_PROVIDER_ENV', 'count': 1}, {'reason_code': 'SKIP_RATE_HIGH', 'count': 1}]
- rollback: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
- artifact: docs/evidence/s27-04/incident_triage_pack_latest.json
```
