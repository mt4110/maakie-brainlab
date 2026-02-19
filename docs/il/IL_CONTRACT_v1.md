# IL Contract v1（IL-as-LLM）

## Version
- contract: `il_contract_v1`

## Keywords（規約）
この文書では以下を使う：
- MUST: 必須（破ったら契約違反）
- SHOULD: 推奨（理由があれば例外可。ただし evidence に残す）
- MAY: 任意

## Purpose
LLM 出力を “検証可能な中間言語（IL: Intermediate Language）” として扱うための契約。
人間向け会話ではなく、機械が検証し、再現できることが目的。

---

## Contract Surface（I/O）

### Input（LLMへ渡すもの：最低限）
LLM は以下を「入力として与えられたもの」とみなし、**入力以外の情報を捏造しない**。

- prompt（目的）
- context（前提・既存状態）
- constraints（禁止事項・決定論ルール）
- artifact pointers（参照すべき成果物の “場所”）
- previous IL（任意：差分生成など）

#### artifact pointers の規約（MUST）
- MUST: repo ルート基準の **相対パス**
- MUST: 区切りは `/`（POSIX）
- MUST NOT: `file[:\/\/]\/\/` を含む
- MUST NOT: 絶対パス（`/Users/...` 等）
- MUST NOT: `..` を含む（参照の脱出を防ぐ）
- SHOULD: 参照対象が重要なら `sha256` を併記（evidence 側でも可）

### Output（LLMが返すもの）
Top-level JSON object（この形以外は契約違反）：

- `il` (object, required): 実行・検証対象の中間言語
- `meta` (object, required): version / generator / policy
- `evidence` (object, required): hashes / notes（監査の足場）
- `errors` (array, optional): **存在して 1件でも入っていたら FAIL**

#### Success / Failure（MUST）
- Success: `errors` を **出さない**（省略）
- Failure: `errors` を **必ず出す**（length>=1）

#### meta（MUST）
- MUST: `meta.version == "il_contract_v1"`
- SHOULD: `meta.generator`（例：`"human"` / `"gpt"` / `"local-llm"` など）

---

## Canonicalization（決定論：S17-02の canonicalizer/validator が従う規則）

> 目的：同じ意味の IL が **必ず同一バイト列**になること。
> ここでは “canonical JSON bytes” を定義する。

### Encoding（MUST）
- MUST: UTF-8
- MUST NOT: BOM
- MUST: canonical JSON bytes は **末尾改行なし**
- MUST: パック内のテキストファイル改行は LF（`\n`）
- MUST: sort_keys=True
- MUST: separators=(",", ":") (no spaces)
- MUST: ensure_ascii=False
- MUST: allow_nan=False

### Object / Key Order（MUST）
- MUST: object keys は **lexicographic ascending**（辞書順）
- MUST: keys は **ASCII のみ**（`[A-Za-z0-9_./-]`）
  - ※非ASCIIキーは並び順の解釈戦争を呼ぶので v1 では禁止

### Arrays（MUST）
- MUST: arrays は **順序保持**（並べ替え禁止）
- MUST: arrays の並び順は **入力（artifact pointers 等）から決定可能**であること
- IF 並び順が入力から決定できない THEN
  - ERROR（曖昧継続禁止）
- END

### Whitespace（MUST：契約で固定）
- MUST: canonical JSON bytes は **コンパクト表現**
  - 余計な空白・改行・インデントを含まない（`,`, `:` の後に空白なし）
- NOTE: examples は可読のため整形してよいが、canonicalizer はコンパクトで出力する

### Strings（MUST）
- MUST: 制御文字は JSON escape
- MUST NOT: 文字列に `\r`（CR）を含めない
- MUST: 改行は `\n` に統一（raw CRLF の混入禁止）
- SHOULD: IL に “巨大な生テキスト” を埋め込まない（下の上限を参照）

### Numbers（MUST：再現性優先の制限）
- MUST NOT: NaN / Infinity
- MUST: `0.0` に正規化（`-0.0` は禁止・正規化対象）
- MUST: **整数のみ**（fraction / exponent 禁止）
- SHOULD: 範囲は signed 53-bit（`[-(2^53-1), +(2^53-1)]`）
  - 小数が必要なら **文字列**で表現し、単位・scale を明記する

### null / missing / empty（MUST）
- MUST NOT: `null` を使わない（optional は **欠落**で表現）
- MUST: empty string を “欠落の代替” に使わない（欠落は欠落）

---

## Forbidden（禁止：見つけたら契約違反）
### 時刻の捏造（MUST NOT）
- MUST NOT: `created_at`, `generated_at`, `timestamp`, `now` を出力（il/meta/evidence）に含める
  - ※入力 artifact に明示的に存在する値を **コピー**する場合は、S17-02で “例外手続き” を実装するまで v1 では禁止

### 乱数 / 一意IDの捏造（MUST NOT）
- MUST NOT: `uuid`, `nonce`, `random` 等の “非決定論” を含める（固定生成規約なし）

### 巨大テキスト埋め込み（SHOULD NOT）
- SHOULD NOT: 4096 bytes を超える文字列を IL に埋め込む
  - 必要なら artifact pointer + hash で参照する（evidence に残す）

---

## Error Policy（停止規約）
- ERROR が出たら **即停止**（“それっぽいIL”を出さない）
- `errors[]` が 1件でもあれば FAIL（validator が落とす）
- SKIP は “理由1行” + “影響範囲” を `evidence.notes` に書く（監査ログ）

### errors[] item（推奨フォーマット）
- `code` (string, required): `E_SCHEMA|E_FORBIDDEN|E_AMBIGUOUS|E_MISSING_ARTIFACT|E_NONDETERMINISTIC|E_UNSUPPORTED`
- `message` (string, required)
- `path` (string, optional): JSON Pointer 形式推奨
- `hint` (string, optional)

---

## Examples
- `docs/il/examples/good_min.json`（PASS: 最小成功例）
- `docs/il/examples/bad_min.json`（FAIL: schema違反）
- `docs/il/examples/bad_forbidden_timestamp.json`（FAIL: **schema PASS だが contract FAIL**）
