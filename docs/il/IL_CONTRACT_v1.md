# IL Contract v1（IL-as-LLM）

## Version
- contract: `il_contract_v1`

## Purpose
LLM 出力を “検証可能な中間言語（IL）” として扱うための契約。
人間が読むためではなく、機械が検証し再現できるために存在する。

## Output Shape（LLMはこれだけを返す）
Top-level JSON object:

- `il` (object, required): 実行・検証対象の中間言語
- `meta` (object, required): version / generator / policy
- `evidence` (object, required): hashes / notes（検証の足場）
- `errors` (array, optional): 1件でもあれば FAIL

## Canonicalization（決定論）
- keys: lexicographic ascending
- newline: LF
- numbers: NaN/Infinity forbidden, -0 forbidden
- timestamps: prohibited unless explicitly provided as an input artifact (and then must be copied verbatim)

## Forbidden
- “現在時刻で埋める created_at”
- 乱数 / UUID（固定生成規約なし）
- 検証対象 field への曖昧語の混入

## Error Policy
- `errors[]` が存在し length>0 -> FAIL
- SKIP は 1行理由 + 影響範囲（監査ログ）

## Examples
See `docs/il/examples/`.
