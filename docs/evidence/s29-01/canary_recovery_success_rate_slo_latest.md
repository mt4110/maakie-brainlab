# S29-01 Canary Recovery Success-rate SLO v2 (Latest)

- CapturedAtUTC: `2026-02-27T11:27:55Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `d968bc83a6767578fffbc56c901cf072f5b33255`

## Summary

- status: `WARN`
- reason_code: `RECOVERY_REQUIRED`
- trailing_nonpass_streak: `3`
- skip_rate: `1.0`
- recovery_success_rate: `0.0`
- recovery_attempts: `2`
- recovery_slo_level: `SOFT_WARN`

## Recommended Actions

- Validate provider env variables (`base_url/api_key/model`) in runtime and CI contexts.
- Run strict canary once and verify status transition to PASS after recovery action.
- Keep rollback path ready: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
- Improve canary auto-recovery success-rate via strict retry/rollback validation and provider env hardening.

## PR Body Snippet

```md
### S29-01 Canary Recovery Success-rate SLO v2
- status: WARN
- reason_code: RECOVERY_REQUIRED
- trailing_nonpass_streak: 3
- skip_rate: 1.0
- recovery_success_rate: 0.0
- recovery_attempts: 2
- artifact: docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json
```
