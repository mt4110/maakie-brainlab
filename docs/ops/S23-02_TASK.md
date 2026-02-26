# S23-02 TASK — Natural Language to IL Compile Contract v1
Last Updated: 2026-02-26

## Checklist
- [x] 既存契約（IL/ENTRY/EXEC）との境界を整理
- [x] `docs/il/IL_COMPILE_CONTRACT_v1.md` 初版を起票
- [x] compile 入出力・失敗規約・決定論ノブを固定
- [x] S23-03 実装に使う CLI I/F 案を明記
- [ ] `scripts/il_compile.py` 実装着手
- [ ] compile 成功/失敗ケースの unit test 追加
- [ ] `il_entry` 連携 smoke の最小導線を確認

## Expected Evidence
- `rg -n "IL_COMPILE_CONTRACT_v1|IL_COMPILE_OUTPUT_v1|IL_COMPILE_REQUEST_v1" docs/il docs/ops/S23-02_*`
- `git diff -- docs/il/IL_COMPILE_CONTRACT_v1.md docs/ops/S23-02_PLAN.md docs/ops/S23-02_TASK.md`
