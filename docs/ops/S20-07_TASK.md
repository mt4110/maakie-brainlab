# S20-07 Python Compatibility Fix (tomli)

## Task (Fixed Order)
- [ ] Step1: docs/ops に「py<3.11 は tomli が必要」を1行追記（監査ログ） -> Done in PLAN
- [ ] Step2: requirements.txt / pyproject.toml に tomli を明示
- [ ] Step3: tests 実行手順を `python3 -m unittest discover ...` に統一
- [ ] Step4: verify (unittest -> reviewpack verify-only)
