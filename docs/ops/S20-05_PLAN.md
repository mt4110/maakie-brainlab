# S20-05 PLAN: Keyword Precision Tuning

## Goal
- Audit Logs のノイズ低減（Mixed Hallucination 誤検知防止）
- get_keywords() の精度向上（不要語排除、必要な語の取りこぼし防止）

## Specification (Scope: P2)

### 1. Unicode Coverage
- **Core CJK**: `\u4E00-\u9FFF` (Existing)
- **Extensions**: Add Ext-A (`\u3400-\u4DBF`) and Compatibility (`\uF900-\uFAFF`).
- **Hiragana Policy**: **EXCLUDED** (`\u3040-\u309F`).
    - Explicitly excluded to allow natural segmentation of noun phrases (e.g. "重要な点" -> "重要", "点"). Including Hiragana causes entire sentences to become single tokens, increasing false positives.
- **Katakana**: `\u30A0-\u30FF` (Included).

### 2. Stopwords (Japanese)
- **Problem**: "結論", "根拠", "参照", "可能", "ため", "通常" などがキーワードとして抽出され、幻覚判定のノイズになる。
- **Solution**: 明示的な `STOPWORDS` セットを定義し、除外する。
- **Initial Set**: `{"結論", "根拠", "参照", "答え", "回答", "質問", "以下", "概要", "詳細", "点", "面", "場合", "こと", "もの", "ため", "よう", "際", "時", "一般", "的"}`

### 3. Alphanumeric Precision
- **Problem**: "20260217" のような日付やIDの数字の羅列がキーワード扱いされる。
- **Solution**:
    - 数字のみ (`^\d+$`) は除外。
    - 英数字の場合は、最低1文字のアルファベットまたはCJK文字を含むこと（`[a-zA-Z]` check）。
    - 既存の URL (`http...`) 除外は維持。

## Pseudocode
```python
def get_keywords(text):
    # Regex: 
    # CJK: \u4E00-\u9FFF | \u3400-\u4DBF | \uF900-\uFAFF
    # Kana: \u30A0-\u30FF (Katakana only)
    # AlphaNum: [a-zA-Z0-9_]+
    # Exclude: ^\d+$ (Pure digits)
    # Filter: k not in STOPWORDS
    pass
```

## Risks
- Hiragana exclusion might miss pure hiragana keywords (e.g. "りんご").
- -> Accepted risk for P2. RAG keywords usually favor Kanji/Katakana/English. "りんご" appearing alone is rare in technical context, or matches via other means (English "Apple").
