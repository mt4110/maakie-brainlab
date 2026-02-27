# S25-09 LangChain PoC (Latest)

- CapturedAtUTC: `2026-02-27T01:11:57Z`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `3261f6f9720514bfcedefa08c1beb8be2b1ed3c3`
- Config: `docs/ops/S25-09_LANGCHAIN_POC.toml`

## Smoke Results

- overall_status: `PASS`
- poc_smoke: `PASS` (langchain-core)
- rollback_smoke: `PASS` (rollback-native)
- retrieval_rows: `1`

## Rollback

- command: `python3 scripts/ops/s25_langchain_poc.py --mode rollback-only`

## PR Body Snippet

```md
### S25-09 LangChain PoC
- status: PASS
- poc_smoke: PASS (langchain-core)
- rollback_smoke: PASS (rollback-native)
- retrieval_rows: 1
- rollback: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
- artifact: docs/evidence/s25-09/langchain_poc_latest.json
```
