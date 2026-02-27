# S29-02 Taxonomy Pipeline Integration v2 (Latest)

- CapturedAtUTC: `2026-02-27T11:27:55Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `d968bc83a6767578fffbc56c901cf072f5b33255`

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
