# S25-09 LangChain PoC Runbook

## Goal

- Connect SQLite retrieval output to a minimal LangChain flow.
- Keep an immediate rollback path without LangChain.
- Persist smoke results as JSON/Markdown evidence.

## Commands

- PoC + rollback smoke:
  - `make s25-langchain-poc`
- PoC smoke only:
  - `python3 scripts/ops/s25_langchain_poc.py --mode poc-only`
- Rollback smoke only:
  - `python3 scripts/ops/s25_langchain_poc.py --mode rollback-only`

## Artifacts

- Config SOT:
  - `docs/ops/S25-09_LANGCHAIN_POC.toml`
- Latest evidence:
  - `docs/evidence/s25-09/langchain_poc_latest.json`
  - `docs/evidence/s25-09/langchain_poc_latest.md`

## Rollback

Immediate rollback command:

```bash
python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
```

If LangChain dependency is unavailable, PoC smoke is recorded as `SKIP` and rollback smoke remains executable.
