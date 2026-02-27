# S26-05 Regression Safety (Latest)

- CapturedAtUTC: `2026-02-27T02:44:04.525788+00:00`
- Branch: `ops/S26-05-S26-06`
- HeadSHA: `a08cc857a66433f18ad8bc366d5e70e84a9795c3`

## Summary

- command_passed: `11/11`
- contract_breaks: `0`
- total_duration_sec: `0.745`

## Commands

- PASS: `make ops-now` (`0.108s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_provider_canary.py` (`0.103s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_medium_eval_wall.py` (`0.054s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_rollback_artifact.py` (`0.059s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_orchestration_core.py` (`0.056s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_regression_safety.py` (`0.058s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_acceptance_wall.py` (`0.061s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_reliability_report.py` (`0.059s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_evidence_index.py` (`0.073s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_release_readiness.py` (`0.056s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_closeout.py` (`0.058s`) rc=0

## Contract

- OK: non-blocking marker detected

## PR Body Snippet

```md
### S26-05 Regression Safety
- command_passed: 11/11
- contract_breaks: 0
- total_duration_sec: 0.745
- artifact: docs/evidence/s26-05/regression_safety_latest.json
```
