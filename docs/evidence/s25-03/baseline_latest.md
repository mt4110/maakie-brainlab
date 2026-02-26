# S25-03 Baseline Freeze (Latest)

- CapturedAtUTC: `2026-02-26T23:46:48.783147+00:00`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `754475298c2985d81a1e5c32250acb826fd063fd`

## Baseline Metrics

- Quality: `5/5` commands passed
- Quality(eval pass rate): `100.0%`
- Speed(total): `0.53 sec`
- Cost(command count): `5`
- Current task progress at freeze: `65%`

## Commands

- `PASS` `0.087s` `make ops-now`
- `PASS` `0.045s` `python3 -m unittest -v tests/test_current_point.py`
- `PASS` `0.061s` `python3 tests/test_il_entry_smoke.py`
- `PASS` `0.202s` `make verify-il-thread-v2`
- `PASS` `0.135s` `python3 eval/run_eval.py --mode verify-only --provider mock --dataset rag-eval-wall-v1__seed-mini__v0001`

## PR Body Snippet

```md
### S25-03 Baseline Freeze
- quality: 5/5 commands passed
- eval pass rate: 100.0%
- speed: total 0.53 sec
- cost: 5 commands
- artifact: docs/evidence/s25-03/baseline_latest.json
```
