# S23-02 PLAN — Natural Language to IL Compile Contract v1
Last Updated: 2026-02-26

## Goal
- 自然文要求を IL JSON に変換する「compile」工程の契約を固定する。

## Why Now
- S23-03 以降で LocalLLM を IL実行系へ接続する前に、入出力・失敗・決定論の境界を固定する必要がある。
- ここが曖昧だと、`validator`/`executor`/`eval` の責務が崩れて回帰が増える。

## Acceptance Criteria
- `docs/il/IL_COMPILE_CONTRACT_v1.md` を作成し、以下を定義する:
  - compile input envelope
  - compile output shape (`il/meta/evidence` or structured errors)
  - fail-closed policy
  - determinism knobs (temperature/seed/settings)
  - observability artifacts
- `S23-03` 実装時にそのまま使えるコマンドI/F案を含む。

## Impacted Files
- `docs/il/IL_COMPILE_CONTRACT_v1.md` (new)
- `docs/ops/S23-02_PLAN.md`
- `docs/ops/S23-02_TASK.md` (new)

## Design (v1)
- compile は `scripts/il_compile.py --request <json> --out <dir>` を標準I/Fとする。
- success output は `IL_CONTRACT_v1` 成功形（`il/meta/evidence`）に一致させる。
- failure output は `errors[]` のみを返し、execute に進ませない（fail-closed）。
- すべての run で report/request/prompt/raw_response を `--out` に残し、監査可能にする。

## Non-Goals
- LocalLLM 実装コードの追加
- executor ANSWER 実装
- CI required checks 追加
