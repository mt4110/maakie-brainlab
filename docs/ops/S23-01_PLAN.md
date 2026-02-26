# S23-01 PLAN — IL Entry `--out` Contract Fix
Last Updated: 2026-02-26

## Goal
- `scripts/il_entry.py` の `--out` オプションを実際のOBS出力先として機能させる。

## Why Now
- 現状は `--out` を受け取っているが未反映で、契約と実装が不一致。
- S23系（compile/execute/e2e）の前提として、出力先の制御は最初に固定が必要。

## Acceptance Criteria
- `python3 scripts/il_entry.py <il> --out <dir>` 実行時、`<dir>` 配下に成果物が出る。
- stdout の `obs_dir` 表示が実際の出力先と一致する。
- `--out` 未指定時は既存の `.local/obs/il_entry_<UTC>` を維持する。
- 追加テストで `--out` 契約を回帰防止できる。

## Impacted Files
- `scripts/il_entry.py`
- `tests/test_il_entry_outdir.py` (new)
- `docs/ops/S23-01_PLAN.md`
- `docs/ops/S23-01_TASK.md`

## Non-Goals
- LocalLLMのANSWER実装
- RAG opcode stubの置換
- evaluator/CI gateの拡張

