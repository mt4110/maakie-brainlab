# S28-01 Provider Canary Recovery (Latest)

- CapturedAtUTC: `2026-02-27T10:16:33Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `2a3af57247941708ebc55133a88ee4900018b6aa`

## Summary

- status: `WARN`
- reason_code: `RECOVERY_REQUIRED`
- trailing_nonpass_streak: `3`
- skip_rate: `1.0`

## Recommended Actions

- Validate provider env variables (`base_url/api_key/model`) in runtime and CI contexts.
- Run strict canary once and verify status transition to PASS after recovery action.
- Keep rollback path ready: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only

## PR Body Snippet

```md
### S28-01 Provider Canary Recovery
- status: WARN
- reason_code: RECOVERY_REQUIRED
- trailing_nonpass_streak: 3
- skip_rate: 1.0
- artifact: docs/evidence/s28-01/provider_canary_recovery_latest.json
```
