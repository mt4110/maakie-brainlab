# S25-05 Regression Safety (Latest)

- CapturedAtUTC: `2026-02-27T01:11:40.359336+00:00`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `3261f6f9720514bfcedefa08c1beb8be2b1ed3c3`

## Safety Metrics

- Verify compatibility: `4/4` commands passed
- Contract breaks: `0`
- Speed(total): `1.58 sec`

## Commands

- `PASS` `0.709s` `make verify-il`
- `PASS` `0.666s` `bash ops/required_checks_sot.sh check`
- `PASS` `0.045s` `python3 ops/ci/check_required_checks_contract.py`
- `PASS` `0.16s` `python3 -m unittest -v tests/test_required_checks_contract.py`

## Contract Check

- OK: no forbidden required contexts detected

## PR Body Snippet

```md
### S25-05 Regression Safety
- verify_compatibility: 4/4 commands passed
- contract_breaks: 0
- speed: total 1.58 sec
- artifact: docs/evidence/s25-05/regression_safety_latest.json
```
