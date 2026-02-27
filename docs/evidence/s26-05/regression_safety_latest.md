# S26-05 Regression Safety (Latest)

- CapturedAtUTC: `2026-02-27T03:23:27.239922+00:00`
- Branch: `ops/S26-05-S26-06`
- HeadSHA: `da8b651872e89285070085d2bf52564506c830f5`

## Summary

- command_passed: `11/11`
- contract_breaks: `0`
- total_duration_sec: `1.138`

## Commands

- PASS: `make ops-now` (`0.101s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_provider_canary.py` (`0.274s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_medium_eval_wall.py` (`0.122s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_rollback_artifact.py` (`0.058s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_orchestration_core.py` (`0.07s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_regression_safety.py` (`0.056s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_acceptance_wall.py` (`0.15s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_reliability_report.py` (`0.14s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_evidence_index.py` (`0.056s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_release_readiness.py` (`0.055s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_closeout.py` (`0.056s`) rc=0

## Contract

- OK: non-blocking marker detected

## PR Body Snippet

```md
### S26-05 Regression Safety
- command_passed: 11/11
- contract_breaks: 0
- total_duration_sec: 1.138
- artifact: docs/evidence/s26-05/regression_safety_latest.json
```
