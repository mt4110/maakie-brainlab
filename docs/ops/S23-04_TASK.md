# S23-04 TASK — Compile→Entry Thread Runner v2
Last Updated: 2026-02-26

## Progress
- S23-04: 100% (done)

## Checklist
- [x] `IL_THREAD_RUNNER_V2_CONTRACT` の初版を作成（mode/fail-closed/artifacts/determinism）
- [x] `scripts/il_thread_runner_v2.py` を追加（`--cases --mode --out`）
- [x] case単位の compile 実行と entry 連携（run時のみ）を実装
- [x] compile失敗時の fail-closed（entry未実行 + structured error保持）を実装
- [x] `scripts/il_thread_runner_v2_smoke.py` を追加（validate-only/run の最小2ケース）
- [x] `tests/test_il_thread_runner_v2.py` を追加（mode契約とfail-closed回帰）
- [x] `Makefile` に軽量導線を追加（`verify-il` へ smoke 接続）
- [x] ローカル軽量ゲートを実行して証跡を残す

## Expected Evidence
- `git diff -- docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md docs/ops/S23-04_PLAN.md docs/ops/S23-04_TASK.md`
- `python3 -m unittest -v tests.test_il_thread_runner_v2`
- `python3 scripts/il_thread_runner_v2_smoke.py`
- `make verify-il`
