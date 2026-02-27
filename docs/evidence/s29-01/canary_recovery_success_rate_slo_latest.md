# S29-01 Canary Recovery Success-rate SLO (Latest)

- CapturedAtUTC: `2026-02-27T11:07:47Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `4d5916728a1831687c05062a875520825c77e1db`

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
### S29-01 Canary Recovery Success-rate SLO
- status: WARN
- reason_code: RECOVERY_REQUIRED
- trailing_nonpass_streak: 3
- skip_rate: 1.0
- recovery_success_rate: 0.0
- recovery_attempts: 2
- artifact: docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json
```
