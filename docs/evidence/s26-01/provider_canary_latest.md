# S26-01 Provider Canary (Latest)

- CapturedAtUTC: `2026-02-27T02:18:09Z`
- Branch: `ops/S26-01-S26-02`
- HeadSHA: `c2a004b33b9663faad5c42306a321601d7a2512f`
- Config: `docs/ops/S26-01_PROVIDER_CANARY.toml`
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
