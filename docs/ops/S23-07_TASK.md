# S23-07 TASK — Entry Retry Policy for Thread Runner
Last Updated: 2026-02-26

## Progress
- S23-07: 100% (done)

## Checklist
- [x] `--entry-retries` オプションを追加（default=0）
- [x] entry 失敗時の retry ループを実装
- [x] case record に `entry_attempts` を追加
- [x] attempt別 stdout/stderr artifact を保存
- [x] retry成功テストを追加
- [x] retry枯渇テストを追加
- [x] 既存テストと verify-il を再実行

## Expected Evidence
- `python3 -m unittest -v tests.test_il_thread_runner_v2`
- `python3 scripts/il_thread_runner_v2_smoke.py`
- `make verify-il`
