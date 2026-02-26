# S23-01 TASK — IL Entry `--out` Contract Fix
Last Updated: 2026-02-26

## Checklist
- [x] `--out` 契約不整合の確認（実装が未反映）
- [x] `scripts/il_entry.py` で `--out` を実出力先に反映
- [x] `--out` の挙動を確認するテスト追加
- [x] 既存軽量ゲートを再実行して回帰確認

## Expected Evidence
- `python3 -m py_compile scripts/il_entry.py`
- `python3 -m unittest -v tests.test_il_entry_outdir`
- `make verify-il`
