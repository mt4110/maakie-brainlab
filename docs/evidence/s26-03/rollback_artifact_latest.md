# S26-03 Rollback Artifact (Latest)

- CapturedAtUTC: `2026-02-27T03:23:26Z`
- Branch: `ops/S26-05-S26-06`
- HeadSHA: `da8b651872e89285070085d2bf52564506c830f5`

## Summary

- overall_status: `PASS`
- reason_code: ``
- rollback_returncode: `0`

## Upstream

- canary_status: `SKIP`
- medium_status: `PASS`

## Rollback

- command: `python3 scripts/ops/s25_langchain_poc.py --mode rollback-only`

## PR Body Snippet

```md
### S26-03 Rollback Artifact
- status: PASS
- reason_code: 
- rollback_command: python3 scripts/ops/s25_langchain_poc.py --mode rollback-only
- rollback_returncode: 0
- artifact: docs/evidence/s26-03/rollback_artifact_latest.json
```
