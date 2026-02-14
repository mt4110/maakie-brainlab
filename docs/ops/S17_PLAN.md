# S17: IL-as-LLM Contract v1（LLMを中間言語コンパイラとして扱う契約）

## 目的（Why）
LLM 出力を「自然言語」ではなく **検証可能な中間言語（IL: Intermediate Language）**として扱うための契約を定義し、
“賢さ” ではなく **再現性・監査性・決定論**で勝つ。

## スコープ（What）
S17 は 4フェーズ固定（進捗ブレ殺し運用）。

- **S17-00: Kickoff**
  - 目的/用語/非ゴール/成果物/ゲートを固定
- **S17-01: IL Contract v1 Spec**
  - 入出力・正規化・禁止事項・エラー定義・例（GOOD/BAD）を **仕様として確定**
- **S17-02: Validator/Writer**
  - 最小実装（canonicalizer + validator + writer）で **検証可能な形に落とす**
- **S17-03: reviewpack 統合**
  - verify-only と契約を結線し、テストと closeout を完成させる

## 非ゴール（Not Goals）
- LLM の推論品質向上、プロンプト最適化競争
- 意味理解の高度化（semantic correctness を機械的に保証すること）
- 生成文の美しさ、創造性、会話品質
- 「たまたま当たる」挙動の許容（再現不能は敗北）

## 用語（Terms）
- **IL（Intermediate Language）**: LLM が出力する “機械検証可能なJSON”
- **Contract**: 入出力・禁止事項・正規化・エラー規約の集合
- **Canonicalization（正規化）**: 同じ意味のILが必ず同一バイト列になる規則
- **Validator**: IL が契約に適合しているかの機械検証
- **Writer**: IL を保存し、証拠（hash/log/meta）を生成する最小出力器
- **Evidence**: 監査用のログ・ハッシュ・メタ情報（再現性のための最小証拠）

## 成果物（Deliverables）
S17 の成果物は「ドキュメント」と「コード」の両輪。

### Docs（仕様）
- `docs/il/IL_CONTRACT_v1.md`（契約本文：入出力/禁止/エラー/例）
- `docs/il/il.schema.json`（JSON Schema：最低限）
- `docs/il/examples/good_*.json` / `docs/il/examples/bad_*.json`
- `docs/ops/S17-01_PLAN.md` / `docs/ops/S17-01_TASK.md`（設計と順序固定）

### Code（最小実装）
- canonicalizer（入力IL -> canonical JSON bytes）
- validator（schema + rule checks）
- writer（il + evidence 出力）
- tests（GOODはPASS / BADはFAIL、canonicalが安定）

※実装ファイルのパスは S17-02 で repo 構造に合わせて固定（探索→確定→記録）。

## ゲート（Gates）
すべて **clean tree 前提**。dirty なら ERROR（混入を防ぐ）。

- `make test`
- `go run cmd/reviewpack/main.go submit --mode verify-only`

## 進捗率の定義（Progress）
- S17 全体は 4フェーズ均等（各25%）
- 各フェーズ内は Task.md のチェック数で線形に進捗を算出（主観禁止）

## 失敗ポリシー（Failure Policy）
- **曖昧継続禁止**：Error を握りつぶして続行しない
- **SKIP は理由1行**：未来の監査ログになる
- **仕様の例外は docs に残す**：口頭の例外は腐る
