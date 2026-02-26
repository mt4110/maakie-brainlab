# S25-05 Regression Safety (Latest)

- CapturedAtUTC: `2026-02-26T23:40:55.332649+00:00`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `650b76ce2782dd2141d3dd17e8ffcdab44ba4d65`

## Safety Metrics

- Verify compatibility: `4/4` commands passed
- Contract breaks: `0`
- Speed(total): `2.125 sec`

## Commands

- `PASS` `0.652s` `make verify-il`
- `PASS` `1.279s` `bash ops/required_checks_sot.sh check`
- `PASS` `0.058s` `python3 ops/ci/check_required_checks_contract.py`
- `PASS` `0.136s` `python3 -m unittest -v tests/test_required_checks_contract.py`

## Contract Check

- OK: no forbidden required contexts detected

## PR Body Snippet

```md
### S25-05 Regression Safety
- verify_compatibility: 4/4 commands passed
- contract_breaks: 0
- speed: total 2.125 sec
- artifact: docs/evidence/s25-05/regression_safety_latest.json
```
