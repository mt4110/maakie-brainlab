# S28-01 Provider Canary Recovery (Latest)

- CapturedAtUTC: `2026-02-27T07:09:13Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `81102446eb5a9f461a4baf4b243286fc004d9ed4`

## Summary

- status: `WARN`
- reason_code: `RECOVERY_REQUIRED`
- trailing_nonpass_streak: `3`
- skip_rate: `1.0`

## Recommended Actions

- Validate provider env variables and credentials wiring.
- Run strict canary once and verify status transition to PASS.
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
