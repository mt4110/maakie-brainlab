# S29-01 Canary Recovery Success-rate SLO v2 (Latest)

- CapturedAtUTC: `2026-02-27T13:58:17Z`
- Branch: `ops/S30-1-S30-900`
- HeadSHA: `eb11d99e73e0ea59ecc59aaa2c776cca1825a752`

## Summary

- status: `PASS`
- reason_code: ``
- trailing_nonpass_streak: `0`
- skip_rate: `0.0833`
- recovery_success_rate: `1.0`
- recovery_attempts: `3`
- recovery_slo_level: `PASS`

## Recommended Actions

- Validate provider canary config/policy file schema and referenced paths.
- Keep rollback path ready: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only

## PR Body Snippet

```md
### S29-01 Canary Recovery Success-rate SLO v2
- status: PASS
- reason_code: 
- trailing_nonpass_streak: 0
- skip_rate: 0.0833
- recovery_success_rate: 1.0
- recovery_attempts: 3
- artifact: docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json
```
