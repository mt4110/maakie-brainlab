# S26-03 Rollback Artifact (Latest)

- CapturedAtUTC: `2026-02-27T02:18:09Z`
- Branch: `ops/S26-01-S26-02`
- HeadSHA: `c2a004b33b9663faad5c42306a321601d7a2512f`

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
