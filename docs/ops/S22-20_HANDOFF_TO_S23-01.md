# S22-20 HANDOFF TO S23-01
Last Updated: 2026-02-26

## Confirmed Contracts (from S22-17..S22-19)
- merge guard:
  - required checks / failing checks は blocking
  - milestone系は non-blocking（観測 + best-effort autofix）
  - mergeは merge-commit + head SHA pin
- required checks:
  - `ops/required_checks_sot.py` で docs SOT + ruleset SOT を同時照合
  - branch protection が取れない場合は ruleset SOT fallback
- ship flow:
  - `ops/phase_ship.py` で phase指定 ship を共通化
  - PR同期前に `ci-self up --ref <branch>` all-green gate を通す

## S23-01 Kickoff Inputs
- primary refs:
  - `docs/ops/S22-17_PLAN.md`
  - `docs/ops/S22-18_PLAN.md`
  - `docs/ops/S22-19_PLAN.md`
- runtime scripts:
  - `ops/pr_merge_guard.sh`
  - `ops/required_checks_sot.py`
  - `ops/phase_ship.py`

## First Commands (light)
```bash
python3 ops/required_checks_sot.py
bash ops/pr_merge_guard.sh
make phase-ship PHASE=S23-01 SKIP_COMMIT=1 SKIP_PR=1
```

## Known Risks
- `gh`未認証環境では PR同期と live取得が劣化する。
- branch protection API 側の制約時は ruleset SOT fallback 運用になる。
- `phase_ship` は `verify-il` を前提にするため、対象節の gate を変更する場合は追従が必要。

