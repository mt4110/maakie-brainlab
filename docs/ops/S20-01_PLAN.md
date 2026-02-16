# S20-01 Plan — RAG tuning readiness v1 (eval + determinism + injection guard)

## Status
Draft → Implement → Verify → Done

## Goal
RAG/プロンプト/検索パラメータを触り始めても、結果が「気分」にならず、
再現できて、回帰を検知できる状態（＝調整を解禁できる外堀）を固める。

## Background / Problem
- いまはRAGを調整しても「良くなった」の根拠が残りにくい
- Index生成・chunk・検索設定・プロンプトが変わると、結果が揺れる
- Retrieval結果に混ざる命令（prompt injection）を“命令”として扱う事故が起きうる

## Scope (What we do)
### 1) Eval の城壁（調整を科学実験にする）
- 評価セット（質問/期待/根拠）を固定し、実行ログを残す
- 失敗分類（retrieval miss / answer miss / citation miss / injection等）を作る
- 変化は「前回runとの比較」で検知できる（良化/悪化が差分で見える）

### 2) 再現性の堀（同じ入力→同じindex→同じ検索）
- chunk分割・入力正規化・順序を決定論で固定（少なくとも“仕様”として固定）
- index作成の設定（モデル/embedding/チャンク設定/入力スナップショット）を記録できる形にする

### 3) 侵入耐性の門（最低限のガード）
- 「検索結果中の命令」を命令として扱わない方針を明文化
- 最低限の検知ログ（例：危険フレーズ）を出せるようにする（まずは検知でOK）

## Non-Goals
- 最強のRAGを一発で作る
- 大規模なアーキ改造
- 自動生成ツールの作り込み（まずは“計測できる”状態）

## Reserved Paths (S20-01で“置き場所だけ”確定)
このPhaseでは実装しないが、今後の迷子防止のためにパスを予約する。
- Eval spec: `docs/ops/rag/EVAL_SPEC_v1.md`
- Determinism spec: `docs/ops/rag/DETERMINISM_SPEC_v1.md`
- Injection policy: `docs/ops/rag/INJECTION_POLICY_v1.md`

※ `docs/ops/rag/` は S20-01 で作成して良い（中身は薄くてOK、でもパスは固定する）

## Evidence Format (最低限ここまで“形”を固定)
- Eval run の出力は「機械可読 + 人間可読」を両方残せる設計にする
- 失敗分類は、後から集計できる粒度で固定する（名前を変えない）
  - retrieval_miss
  - answer_miss
  - citation_miss
  - hallucination_suspect
  - injection_detected
  - nondeterminism_suspect
  - tool_error

## Deliverables
- `docs/ops/S20-01_PLAN.md`
- `docs/ops/S20-01_TASK.md`
- Update: `docs/ops/ROADMAP.md`（S20 に S20-01 を追記）
- New (spec placeholders):
  - `docs/ops/rag/EVAL_SPEC_v1.md`
  - `docs/ops/rag/DETERMINISM_SPEC_v1.md`
  - `docs/ops/rag/INJECTION_POLICY_v1.md`

## Acceptance Criteria
- 「何を変えたら何が変わったか」が証拠（ログ/差分）として残る設計になっている
- eval の固定セットと実行の出力先が決まっている（再実行できる）
- injection方針が明文化され、最低限の検知が可能
- docs に file URL（fileスキーム） や ユーザHOME絶対パス を混ぜない
- `go test ./...` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

## Evidence / Gates
- `go test ./...`
- `go run cmd/reviewpack/main.go submit --mode verify-only`
