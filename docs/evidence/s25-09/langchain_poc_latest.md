# S25-09 LangChain PoC (Latest)

- CapturedAtUTC: `2026-02-27T01:15:36Z`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `ae5c5b867e5927c416478a5e6ec3ab64bc3386cc`
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
