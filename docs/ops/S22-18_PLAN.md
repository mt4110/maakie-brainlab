# S22-18 PLAN — Required Checks SOT Unification
Last Updated: 2026-02-26

## Goal
- required checks 判定を単一契約に寄せ、`403 bypass` 依存を除去する。

## Acceptance Criteria
- `ops/required_checks_sot.py check` が docs SOT と ruleset SOT を同時照合できる。
- branch protection 取得不能時は ruleset SOT fallback を使い、無条件PASSにしない。
- `ops/pr_merge_guard.sh` が `OK: required_checks_sot matched` 以外で停止する。
- `write-sot` で docs/ruleset のSOTを同期更新できる。

## Impacted Files
- `ops/required_checks_sot.py`
- `ops/pr_merge_guard.sh`
- `docs/ops/S22-18_PLAN.md`
- `docs/ops/S22-18_TASK.md`

## Design
- live source 優先順位:
  - branch protection contexts
  - ruleset SOT fallback
- check mode:
  - live vs docs SOT
  - live vs ruleset SOT
  - 両方一致のみ OK

