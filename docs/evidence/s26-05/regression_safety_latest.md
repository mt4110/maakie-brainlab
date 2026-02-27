# S26-05 Regression Safety (Latest)

- CapturedAtUTC: `2026-02-27T03:33:03.019557+00:00`
- Branch: `ops/S26-05-S26-06`
- HeadSHA: `8af969292a66335f055382f1a5b2e2bdfa330a7c`

## Summary

- command_passed: `11/11`
- contract_breaks: `0`
- total_duration_sec: `1.101`

## Commands

- PASS: `make ops-now` (`0.09s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_provider_canary.py` (`0.317s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_medium_eval_wall.py` (`0.121s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_rollback_artifact.py` (`0.05s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_orchestration_core.py` (`0.067s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_regression_safety.py` (`0.05s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_acceptance_wall.py` (`0.128s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_reliability_report.py` (`0.119s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_evidence_index.py` (`0.047s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_release_readiness.py` (`0.047s`) rc=0
- PASS: `python3 -m unittest -v tests/test_s26_closeout.py` (`0.065s`) rc=0

## Contract

- OK: non-blocking marker detected

## PR Body Snippet

```md
### S26-05 Regression Safety
- command_passed: 11/11
- contract_breaks: 0
- total_duration_sec: 1.101
- artifact: docs/evidence/s26-05/regression_safety_latest.json
```
