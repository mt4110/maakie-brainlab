# S23-05 PLAN — Thread Runner Resilience Hardening
Last Updated: 2026-02-26

## Goal
- `il_thread_runner_v2` が 1 ケースのハングや異常で全体停止しないように、耐停止性を強化する。

## Why Now
- S23-04 で `compile -> entry` 導線はできたが、`entry` 呼び出しが関数直結で timeout 制御がない。
- 実運用で最も避けるべき「止まる」を潰すため、ケース単位タイムアウトと継続実行を先に固定する。

## Acceptance Criteria
- `scripts/il_thread_runner_v2.py` に `--entry-timeout-sec` を追加（defaultあり）。
- `run` モードの `il_entry` 実行を subprocess 化し、timeout時は:
  - 当該caseを `entry_status=ERROR` として記録
  - timeout理由を record に残す
  - 次caseへ継続（runner全体は stopless）
- `entry` の stdout/stderr を case artifact として保存する。
- `tests/test_il_thread_runner_v2.py` に timeout/継続性の回帰テストを追加する。
- 既存の smoke と `make verify-il` が通る。

## Impacted Files
- `docs/ops/S23-05_PLAN.md` (new)
- `docs/ops/S23-05_TASK.md` (new)
- `scripts/il_thread_runner_v2.py`
- `tests/test_il_thread_runner_v2.py`

## Design (v1)
- entry実行:
  - `python3 <entry_script> <compiled.json> --out <entry_dir> [--fixture-db <path>]`
  - `subprocess.run(..., timeout=<entry-timeout-sec>)`
- timeout例外時:
  - `entry_status=ERROR`
  - `entry_stop=1`
  - `entry_error_codes=["E_TIMEOUT"]`
  - `entry_skip_reason=""`
- entry stdout/stderr:
  - `cases/<id>/entry/entry.stdout.log`
  - `cases/<id>/entry/entry.stderr.log`
- テスト用に `--entry-script` を公開オプションとして追加し、sleepするダミースクリプトで timeout を再現可能にする。

## Non-Goals
- executor 本体の性能改善
- compile 側のモデル品質最適化
- 重量級評価（eval wall full run）
