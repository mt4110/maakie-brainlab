# S23-02 TASK — Natural Language to IL Compile Contract v1
Last Updated: 2026-02-26

## Checklist
- [x] 既存契約（IL/ENTRY/EXEC）との境界を整理
- [x] `docs/il/IL_COMPILE_CONTRACT_v1.md` 初版を起票
- [x] compile 入出力・失敗規約・決定論ノブを固定
- [x] S23-03 実装に使う CLI I/F 案を明記
- [x] `scripts/il_compile.py` の最小実装を追加
- [x] compile 成功/失敗ケースの unit test を追加
- [x] `il_entry` 連携 smoke (`scripts/il_compile_entry_smoke.py`) を追加
- [x] `local_llm` provider を差し込み（失敗時 rule-based fallback 維持）
- [x] compile 品質ベンチ (`scripts/il_compile_bench.py`) を追加
- [x] prompt profile 比較ループ (`scripts/il_compile_prompt_loop.py`) を追加
- [x] ベンチ指標を `required_terms/opcodes` の precision/recall/F1 に拡張

## Expected Evidence
- `rg -n "IL_COMPILE_CONTRACT_v1|IL_COMPILE_OUTPUT_v1|IL_COMPILE_REQUEST_v1" docs/il docs/ops/S23-02_*`
- `git diff -- docs/il/IL_COMPILE_CONTRACT_v1.md docs/ops/S23-02_PLAN.md docs/ops/S23-02_TASK.md`
- `python3 -m unittest -v tests.test_il_compile`
- `python3 scripts/il_compile_entry_smoke.py`
- `python3 scripts/il_compile_bench.py --provider rule_based --expand-factor 1`
- `python3 scripts/il_compile_prompt_loop.py --profiles v1,strict_json_v2,contract_json_v3`
