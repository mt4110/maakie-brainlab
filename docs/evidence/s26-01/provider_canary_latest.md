# S26-01 Provider Canary (Latest)

- CapturedAtUTC: `2026-02-27T03:32:17Z`
- Branch: `ops/S26-05-S26-06`
- HeadSHA: `8af969292a66335f055382f1a5b2e2bdfa330a7c`
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
