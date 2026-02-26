# S25-05 Regression Safety (Latest)

- CapturedAtUTC: `2026-02-26T23:46:51.418755+00:00`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `754475298c2985d81a1e5c32250acb826fd063fd`

## Safety Metrics

- Verify compatibility: `4/4` commands passed
- Contract breaks: `0`
- Speed(total): `1.922 sec`

## Commands

- `PASS` `0.607s` `make verify-il`
- `PASS` `1.124s` `bash ops/required_checks_sot.sh check`
- `PASS` `0.051s` `python3 ops/ci/check_required_checks_contract.py`
- `PASS` `0.14s` `python3 -m unittest -v tests/test_required_checks_contract.py`

## Contract Check

- OK: no forbidden required contexts detected

## PR Body Snippet

```md
### S25-05 Regression Safety
- verify_compatibility: 4/4 commands passed
- contract_breaks: 0
- speed: total 1.922 sec
- artifact: docs/evidence/s25-05/regression_safety_latest.json
```
