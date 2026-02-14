# S16-02 PLAN — Repo Absolute Plan/Task Standard (v1)

## Goal
Plan/Task を「再現可能な疑似コード + 固定実行順序」として標準化する。
毎回 “編集対象ファイルの repo 実パス” を確定し、作業の曖昧さを消す。

## Non-Goals
- reviewpack 本体の新機能追加はしない（S16-01で契約強制は完了済み）
- 自動生成CLIの実装はしない（必要ならS17で切る）

## Definitions (MUST)
- **ERROR**: その場で終了。曖昧な継続は禁止。
- **SKIP**: スキップ理由を必ず1行残す（未来の監査ログ）。
- **STOP**: 前提が崩れたら止める（嘘を付かない仕組み）。

## Hard Constraints
- repo / PR本文に 絶対URL (file scheme) を混入させない
- コマンドは状態依存を避け、可能な限り `bash -lc 'set -euo pipefail; ...'` で実行する
- 変更は docs/ops の追加・更新のみ（原則）

## Plan (Pseudo Code)
PHASE 0: Safety Snapshot
  - repo root を確定し、絶対パスで編集対象を列挙する
  - git状態が clean でないなら ERROR（意図が説明できない変更は混ぜない）

PHASE 1: Target Confirmation (Absolute Paths)
  - ROOT := git rev-parse --show-toplevel
  - TARGETS := S16-02/03 の plan/task と S16_PLAN/TASK
  - すべて ROOT からの絶対パスを表示し、存在確認（無ければ作成へ）

PHASE 2: Authoring Rules (the “Type”)
  - Plan.md は疑似コード（分岐/停止条件/for探索/break/continue）
  - Task.md はチェックボックスで順序を固定
  - for は探索に使う：候補を列挙し、見つけたら break、無ければ continue
  - skip は理由1行必須、error はその場で終了

PHASE 3: Write S16-02 Docs
  - S16-02_PLAN.md を作成
  - S16-02_TASK.md を作成（実行順序固定、証拠生成まで）

PHASE 4: Update S16 Index (S16_PLAN / S16_TASK)
  - S16のマイルストーン（S16-00..03）を固定で明記
  - 進捗表記ルールを追記

PHASE 5: Gates + Evidence
  - make test PASS
  - reviewpack submit --mode verify-only PASS
  - スキャンポリシー（禁止URL 0件）を PASS

## Acceptance Criteria (PASS/FAIL)
- docs/ops に S16-02/03 の Plan/Task が存在
- S16_PLAN/TASK が S16-00..03 固定を明記
- `make test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS
- repo内 絶対URL (file scheme) 0 件
