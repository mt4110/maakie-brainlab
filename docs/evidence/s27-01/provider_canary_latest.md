# S26-01 Provider Canary (Latest)

- CapturedAtUTC: `2026-02-27T04:14:21Z`
- Branch: `ops/S27-01-S27-10`
- HeadSHA: `02f0f008326b975d7100e79201a4370e4f5c81aa`
- Config: `docs/ops/S27-01_PROVIDER_CANARY_OPS.toml`
- PolicyHash: `170f1b5a842ef87edbb6297c0fbf1331a9d90dc683eec54340bf86300b6e4c79`

## Summary

- overall_status: `SKIP`
- passed_cases: `0`
- failed_cases: `0`
- skipped_cases: `2`
- reason_code: `MISSING_PROVIDER_ENV`

## Rollback

- command: `python3 scripts/ops/s25_langchain_poc.py --mode rollback-only`

## PR Body Snippet

```md
### S26-01 Provider Canary
- status: SKIP
- passed_failed_skipped: 0/0/2
- reason_code: MISSING_PROVIDER_ENV
- policy_hash: 170f1b5a842ef87edbb6297c0fbf1331a9d90dc683eec54340bf86300b6e4c79
- rollback: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
- artifact: docs/evidence/s26-01/provider_canary_latest.json
```
