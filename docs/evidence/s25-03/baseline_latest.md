# S25-03 Baseline Freeze (Latest)

- CapturedAtUTC: `2026-02-27T01:15:32.154517+00:00`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `ae5c5b867e5927c416478a5e6ec3ab64bc3386cc`

## Baseline Metrics

- Quality: `5/5` commands passed
- Quality(eval pass rate): `100.0%`
- Speed(total): `0.575 sec`
- Cost(command count): `5`
- Current task progress at freeze: `100%`

## Commands

- `PASS` `0.104s` `make ops-now`
- `PASS` `0.052s` `python3 -m unittest -v tests/test_current_point.py`
- `PASS` `0.074s` `python3 tests/test_il_entry_smoke.py`
- `PASS` `0.238s` `make verify-il-thread-v2`
- `PASS` `0.107s` `python3 eval/run_eval.py --mode verify-only --provider mock --dataset rag-eval-wall-v1__seed-mini__v0001`

## PR Body Snippet

```md
### S25-03 Baseline Freeze
- quality: 5/5 commands passed
- eval pass rate: 100.0%
- speed: total 0.575 sec
- cost: 5 commands
- artifact: docs/evidence/s25-03/baseline_latest.json
```
