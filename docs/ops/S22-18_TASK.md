# S22-18 TASK — Required Checks SOT Unification
Last Updated: 2026-02-26

## Checklist
- [x] `required_checks_sot.py` を check/write-sot/dump-live の3モードで整理
- [x] branch protection 不可時に ruleset SOT fallback を実装
- [x] docs SOT と ruleset SOT の二重照合を実装
- [x] `pr_merge_guard` の 403 bypass を削除
- [x] drift出力を docs/ruleset 別に可視化

## Result
- required checks gate は「ライブ取得 + SOT整合」の契約に一本化。
- 取得不能時の無条件PASSを廃止し、fail-closedで扱う。

