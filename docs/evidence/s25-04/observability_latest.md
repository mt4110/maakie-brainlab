# S25-04 Observability Summary (Latest)

- baseline_json: `docs/evidence/s25-03/baseline_latest.json`

## Tools

- `acceptance-wall` run=`acceptance-wall__20260226T234648Z__ops-s25-01-25-10__7544752` OK=16 WARN=0 ERROR=0 SKIP=0
- `baseline-freeze` run=`baseline-freeze__20260227T011137Z__ops-s25-01-25-10__3261f6f` OK=14 WARN=0 ERROR=0 SKIP=0
- `current-point` run=`current-point__20260227T011138Z__ops-s25-01-25-10__3261f6f` OK=7 WARN=0 ERROR=0 SKIP=1
- `langchain-poc` run=`langchain-poc__20260227T001529Z__ops-s25-01-25-10__0e4909a` OK=10 WARN=0 ERROR=0 SKIP=0
- `ml-experiment` run=`ml-experiment__20260226T235148Z__ops-s25-01-25-10__7544752` OK=8 WARN=0 ERROR=0 SKIP=0
- `obs-pr-summary` run=`obs-pr-summary__20260227T000529Z__ops-s25-01-25-10__df64ab4` OK=4 WARN=0 ERROR=0 SKIP=0
- `rag-tuning` run=`rag-tuning__20260227T000529Z__ops-s25-01-25-10__df64ab4` OK=9 WARN=0 ERROR=0 SKIP=0
- `regression-safety` run=`regression-safety__20260227T011128Z__ops-s25-01-25-10__3261f6f` OK=13 WARN=0 ERROR=0 SKIP=0

## PR Body Snippet

```md
### S25-04 Observability
- baseline: docs/evidence/s25-03/baseline_latest.json
- acceptance-wall: run=acceptance-wall__20260226T234648Z__ops-s25-01-25-10__7544752 (OK=16 WARN=0 ERROR=0 SKIP=0)
- baseline-freeze: run=baseline-freeze__20260227T011137Z__ops-s25-01-25-10__3261f6f (OK=14 WARN=0 ERROR=0 SKIP=0)
- current-point: run=current-point__20260227T011138Z__ops-s25-01-25-10__3261f6f (OK=7 WARN=0 ERROR=0 SKIP=1)
- langchain-poc: run=langchain-poc__20260227T001529Z__ops-s25-01-25-10__0e4909a (OK=10 WARN=0 ERROR=0 SKIP=0)
- ml-experiment: run=ml-experiment__20260226T235148Z__ops-s25-01-25-10__7544752 (OK=8 WARN=0 ERROR=0 SKIP=0)
- obs-pr-summary: run=obs-pr-summary__20260227T000529Z__ops-s25-01-25-10__df64ab4 (OK=4 WARN=0 ERROR=0 SKIP=0)
- rag-tuning: run=rag-tuning__20260227T000529Z__ops-s25-01-25-10__df64ab4 (OK=9 WARN=0 ERROR=0 SKIP=0)
- regression-safety: run=regression-safety__20260227T011128Z__ops-s25-01-25-10__3261f6f (OK=13 WARN=0 ERROR=0 SKIP=0)
- contract: levels=OK|WARN|ERROR|SKIP, path=.local/obs/s25-ops/<tool>/<run-id>/
```
