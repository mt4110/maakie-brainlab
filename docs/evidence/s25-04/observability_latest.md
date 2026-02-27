# S25-04 Observability Summary (Latest)

- baseline_json: `docs/evidence/s25-03/baseline_latest.json`

## Tools

- `acceptance-wall` run=`acceptance-wall__20260227T011137Z__ops-s25-01-25-10__3261f6f` OK=16 WARN=0 ERROR=0 SKIP=0
- `baseline-freeze` run=`baseline-freeze__20260227T011532Z__ops-s25-01-25-10__ae5c5b8` OK=14 WARN=0 ERROR=0 SKIP=0
- `current-point` run=`current-point__20260227T011532Z__ops-s25-01-25-10__ae5c5b8` OK=7 WARN=0 ERROR=0 SKIP=1
- `langchain-poc` run=`langchain-poc__20260227T011154Z__ops-s25-01-25-10__3261f6f` OK=10 WARN=0 ERROR=0 SKIP=0
- `ml-experiment` run=`ml-experiment__20260227T011147Z__ops-s25-01-25-10__3261f6f` OK=8 WARN=0 ERROR=0 SKIP=0
- `obs-pr-summary` run=`obs-pr-summary__20260227T011138Z__ops-s25-01-25-10__3261f6f` OK=4 WARN=0 ERROR=0 SKIP=0
- `rag-tuning` run=`rag-tuning__20260227T011151Z__ops-s25-01-25-10__3261f6f` OK=9 WARN=0 ERROR=0 SKIP=0
- `regression-safety` run=`regression-safety__20260227T011530Z__ops-s25-01-25-10__ae5c5b8` OK=13 WARN=0 ERROR=0 SKIP=0

## PR Body Snippet

```md
### S25-04 Observability
- baseline: docs/evidence/s25-03/baseline_latest.json
- acceptance-wall: run=acceptance-wall__20260227T011137Z__ops-s25-01-25-10__3261f6f (OK=16 WARN=0 ERROR=0 SKIP=0)
- baseline-freeze: run=baseline-freeze__20260227T011532Z__ops-s25-01-25-10__ae5c5b8 (OK=14 WARN=0 ERROR=0 SKIP=0)
- current-point: run=current-point__20260227T011532Z__ops-s25-01-25-10__ae5c5b8 (OK=7 WARN=0 ERROR=0 SKIP=1)
- langchain-poc: run=langchain-poc__20260227T011154Z__ops-s25-01-25-10__3261f6f (OK=10 WARN=0 ERROR=0 SKIP=0)
- ml-experiment: run=ml-experiment__20260227T011147Z__ops-s25-01-25-10__3261f6f (OK=8 WARN=0 ERROR=0 SKIP=0)
- obs-pr-summary: run=obs-pr-summary__20260227T011138Z__ops-s25-01-25-10__3261f6f (OK=4 WARN=0 ERROR=0 SKIP=0)
- rag-tuning: run=rag-tuning__20260227T011151Z__ops-s25-01-25-10__3261f6f (OK=9 WARN=0 ERROR=0 SKIP=0)
- regression-safety: run=regression-safety__20260227T011530Z__ops-s25-01-25-10__ae5c5b8 (OK=13 WARN=0 ERROR=0 SKIP=0)
- contract: levels=OK|WARN|ERROR|SKIP, path=.local/obs/s25-ops/<tool>/<run-id>/
```
