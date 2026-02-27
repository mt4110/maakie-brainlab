# S25-03 Baseline Freeze (Latest)

- CapturedAtUTC: `2026-02-27T01:11:37.991978+00:00`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `3261f6f9720514bfcedefa08c1beb8be2b1ed3c3`

## Baseline Metrics

- Quality: `5/5` commands passed
- Quality(eval pass rate): `100.0%`
- Speed(total): `0.563 sec`
- Cost(command count): `5`
- Current task progress at freeze: `100%`

## Commands

- `PASS` `0.102s` `make ops-now`
- `PASS` `0.052s` `python3 -m unittest -v tests/test_current_point.py`
- `PASS` `0.071s` `python3 tests/test_il_entry_smoke.py`
- `PASS` `0.234s` `make verify-il-thread-v2`
- `PASS` `0.104s` `python3 eval/run_eval.py --mode verify-only --provider mock --dataset rag-eval-wall-v1__seed-mini__v0001`

## PR Body Snippet

```md
### S25-03 Baseline Freeze
- quality: 5/5 commands passed
- eval pass rate: 100.0%
- speed: total 0.563 sec
- cost: 5 commands
- artifact: docs/evidence/s25-03/baseline_latest.json
```
