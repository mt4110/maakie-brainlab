# S23-06 TASK — Thread Runner Replay Determinism Gate
Last Updated: 2026-02-26

## Progress
- S23-06: 100% (done)

## Checklist
- [x] replay check スクリプトを追加（2-run比較 + report出力）
- [x] replay用 fixture (`cases_smoke.jsonl`) を追加
- [x] replay check ユニットテストを追加
- [x] mismatch時の `ERROR` ログと report 生成を確認
- [x] ローカル軽量テストを実行

## Expected Evidence
- `python3 -m unittest -v tests.test_il_thread_runner_v2_replay`
- `python3 scripts/il_thread_runner_v2_replay_check.py`
