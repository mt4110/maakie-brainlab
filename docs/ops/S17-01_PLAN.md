# S17-01 PLAN（IL Contract v1 Spec: 検証可能な契約）

## Goal
LLM を “ILコンパイラ” として扱うための契約（入出力・正規化・禁止事項・エラー定義）を
**機械検証可能**な仕様として確定する。

## MUST（譲れない）
- Canonical JSON の規約（順序・改行・数値・null/空文字・改行コード）を明文化
- Error policy：曖昧継続禁止（ERRORは即停止）
- SKIP policy：スキップ理由は必ず1行（監査ログになる）
- GOOD/BAD 例を最低1つずつ（テスト可能な粒度）

## Contract Surface（I/O 定義）

### Input（LLMへ渡すもの）
- prompt（目的）
- context（前提・制約・既存状態）
- constraints（禁止事項・決定論規則）
- artifact pointers（参照すべきファイル/ハッシュ/ID）
- previous IL（任意：差分生成などで使う場合）

### Output（LLMが返すもの）
- `il`: JSON object（必須）
- `meta`: object（必須：version, generator, created_at policy など）
- `evidence`: object（必須：hashes, notes など）
- `errors`: array（任意：ただし errors が1件でもあれば全体は FAIL 扱い）

※ “生成文” は出力に含めない。出すなら `notes` に隔離し、検証対象外にする。

## Canonicalization Rules（決定論）
### JSON Canonical（最低限のルール）
- object keys: **昇順ソート（byte order / lexicographic）**
- arrays: **順序は保持**（並べ替え禁止、並べ替えるなら `sort_key` を明記）
- whitespace: **インデントなし**（または固定インデント幅を spec で固定）
- newline: **LF（\\n）固定**
- number:
  - NaN/Infinity 禁止
  - `-0` 禁止（0に正規化）
  - 先頭ゼロ禁止（"01" 的表現を禁止）
- string:
  - 制御文字は JSON escape
  - 改行は `\\n` に統一（raw CRLF 禁止）
- null/empty:
  - optional field は「欠落」か「null」かを固定（混在禁止）
  - empty string と null を意味的に混同しない（両方使うなら目的を明記）

### Forbidden（禁止）
- 時刻を “現在時刻” で埋める（再現性破壊）
- 乱数 / UUID（固定生成規約なしでの出現は禁止）
- 曖昧表現（"maybe", "probably" 等）が検証対象の field に混入

## Error Policy（停止規約）
- ERROR が出たら **即停止**（継続して“それっぽい結果”を出さない）
- errors[] が 1件でもあれば FAIL（validator が落とす）
- SKIP は “理由1行” + “影響範囲” を書く

## Spec Artifacts（S17-01で作る固定パス）
- `docs/il/IL_CONTRACT_v1.md`
- `docs/il/il.schema.json`
- `docs/il/examples/good_min.json`
- `docs/il/examples/bad_min.json`
- `docs/il/examples/bad_forbidden_timestamp.json`


## Examples（最低限）
- GOOD: schema PASS、canonicalize して安定
- BAD: schema FAIL または rule violation（例：NaN, -0, unsorted keys, forbidden timestamp）

## Acceptance（受け入れ条件）
- Spec doc（IL_CONTRACT_v1.md）が “入出力/禁止/正規化/エラー/例” を含む
- JSON schema が存在し、最低限の構造を検証できる
- GOOD/BAD が最低1つずつあり、S17-02 のテスト素材として使える
