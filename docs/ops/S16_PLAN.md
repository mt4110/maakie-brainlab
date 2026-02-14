# S16: AI Contract Kickoff (IL-as-LLM)

## Goal
AIを「中間言語(IL)」として扱う前提で、入出力・証拠・再現性の契約を先に固定する。

## Non-Goals
- 実装の大量追加（このフェーズではやらない）
- 生成モデルの選定論争（このフェーズでは凍結）

## Milestones (Fixed)
- S16-00: Kickoff（S16_PLAN/S16_TASK 作成）
- S16-01: Closeout（PACK_VERSION v2 導入、AI Contract v1 強制）※merged
- S16-02: Repo-absolute Plan/Task standard（実パス確定・疑似コード/固定順序の型）
- S16-03: Ambi precision command template（デグレ爆速化の“型”）

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
