# S29-02 Taxonomy Pipeline Integration v2 (Latest)

- CapturedAtUTC: `2026-02-27T11:50:23Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `2971732a2c6df3a57166589d92e528ab65e49038`

## Summary

- status: `WARN`
- reason_code: `UNKNOWN_RATIO_ABOVE_TARGET`
- unknown_ratio: `0.3125`
- candidate_count: `5`
- pipeline_records: `5`
- action_count: `4`
- pipeline_jsonl: `docs/evidence/s29-02/taxonomy_pipeline_candidates_latest.jsonl`

## Collection Actions

- Collect at least 2 additional labeled cases for taxonomy 'provider'.
- Collect at least 1 additional labeled cases for taxonomy 'network'.
- Collect at least 1 additional labeled cases for taxonomy 'schema'.
- Collect at least 1 additional labeled cases for taxonomy 'unknown'.
- Promote top unknown candidates to incident triage backlog and assign owner.

## PR Body Snippet

```md
### S29-02 Taxonomy Pipeline Integration v2
- status: WARN
- reason_code: UNKNOWN_RATIO_ABOVE_TARGET
- unknown_ratio: 0.3125
- candidate_count: 5
- pipeline_records: 5
- action_count: 4
- artifact: docs/evidence/s29-02/taxonomy_pipeline_integration_latest.json
```
