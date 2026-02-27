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
- Input:
  - prompt: 実行対象の指示本文（1つ）
  - context: repo root / branch / HEAD / 対象ファイル群
  - artifacts: 既存 evidence と直近の gate 実行ログ
- Output:
  - docs: 対応する `S16*_PLAN.md` / `S16*_TASK.md` の更新
  - checklists: TASK の順序固定チェック項目
  - evidence: verify-only 実行結果（PASS/FAIL と主要ログ）
- Determinism:
  - 実行コマンドは repo-absolute path で固定する
  - 並び順は TASK チェックボックス順を唯一の実行順序とする
  - 生成JSONはキー順固定・比較可能な形で保存する
- Evidence:
  - `make test` の結果
  - `go run cmd/reviewpack/main.go submit --mode verify-only` の結果
  - review bundle filename と sha256

## Acceptance
- docs/ops/S16_PLAN.md と S16_TASK.md が整合
- `go run cmd/reviewpack/main.go submit --mode verify-only` が PASS
- 生成物が“増えても”破綻しない（契約で縛られている）

## Gates
- make test
- `go run cmd/reviewpack/main.go submit --mode verify-only`
