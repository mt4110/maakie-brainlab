# S16: AI Contract Kickoff (IL-as-LLM)

## Goal
AIを「中間言語(IL)」として扱う前提で、入出力・証拠・再現性の契約を先に固定する。

## Non-Goals
- 実装の大量追加（このフェーズではやらない）
- 生成モデルの選定論争（このフェーズでは凍結）

## Contract (Draft)
- Input: (TODO) prompt / context / artifacts の最小セット
- Output: (TODO) 必須の生成物一覧（JSON/MD/TSV など）
- Determinism: (TODO) タイムスタンプ/順序/正規化の規約
- Evidence: (TODO) review_bundle に入るべきログと、そのsha256

## Acceptance
- docs/ops/S16_PLAN.md と S16_TASK.md が整合
- `go run cmd/reviewpack/main.go submit --mode verify-only` が PASS
- 生成物が“増えても”破綻しない（契約で縛られている）

## Gates
- make test
- `go run cmd/reviewpack/main.go submit --mode verify-only`
