# S20-02 Plan — RAG eval wall v1 (dataset + run artifacts + failure taxonomy)

## Status
Draft → Implement → Verify → Done

## Goal
RAG調整を「気分」から引きずり出し、科学実験にする。
固定の評価セット・実行出力・失敗分類を確定し、比較可能な形で証拠を残せるようにする。

## Background / Problem
- 変更（プロンプト/検索/Index）を入れても「良くなった」の根拠が散りやすい
- 実行ログや結果が標準化されておらず、比較が面倒で回帰検知が弱い
- 失敗が“どこで起きたか”分類できず、改善の打ち手がブレる

## Scope (What we do)
### 1) Eval dataset の固定
- 評価データ（質問/期待/根拠/タグ）を固定し、置き場所とフォーマットを仕様化する
- “増やす”は可能だが、既存IDは不変（差分比較を壊さない）

### 2) Eval run artifacts の固定
- 実行の出力先・命名規則・最低限のファイル構成を固定する
- 人間可読（summary）と機械可読（jsonl等）の両方を残せる形を定義する

### 3) Failure taxonomy の固定
- 失敗分類（例：retrieval_miss / answer_miss / citation_miss / injection_detected / nondeterminism_suspect / tool_error）を固定し、
  後から集計できる粒度と命名を“仕様”として凍結する

## Non-Goals
- RAG自体の性能をこのPhaseで上げ切る（ここは計測の基礎固め）
- 大規模アーキ変更
- 自動チューニングの実装

## Deliverables
- `docs/ops/S20-02_PLAN.md`
- `docs/ops/S20-02_TASK.md`
- Update: `docs/ops/ROADMAP.md`（S20 に S20-02 を追記）
- Update (spec深化):
  - `docs/ops/rag/EVAL_SPEC_v1.md`（dataset/run artifacts/taxonomyを具体化）

## Acceptance Criteria
- EVAL_SPEC に以下が明記されている
  - dataset: 置き場所 / フォーマット / IDルール
  - run artifacts: 出力先 / 命名規則 / 最低限のファイル構成
  - failure taxonomy: 名称と意味、集計可能な粒度
- 差分比較（前回run vs 今回run）を行う前提が崩れない（ID/分類名が不変）
- docs に file URL（fileスキーム）やユーザHOME絶対パスを混ぜない
- `go test ./...` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

## Evidence / Gates
- `go test ./...`
- `go run cmd/reviewpack/main.go submit --mode verify-only`
