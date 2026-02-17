# S20-06(P3) PLAN — Keyword Noise Guardrails

## Goal
- get_keywords() の “ノイズ抑制” を仕様として固定する
  1) long-hex (SHA/Git SHA) 除外
  2) 半角カナ取り扱いの固定（normalize / keep / drop のどれかを選び、ブレを封じる）
  3) stopwords に「増やす理由」を1行ずつ残す（監査耐性）

## Non-Negotiable Rules (local/interactive)
- Shell: exit / return 1 / set -e / set -euo pipefail / trap ... EXIT 禁止
- Python: sys.exit / raise SystemExit / assert(文) 禁止
- 失敗は終了コードで制御しない。必ず print で真実だけを残す（OK/ERROR/SKIP）
- 重い処理は分割（1ステップ=1観測）。固まりそうなら中断して「理由+直前の観測」を1行残す。

## Scope Decision (CIについての破綻回避メモ)
- この“exit禁止”は「対話実行の補助スクリプト/あんびちゃそ運用」を対象にする。
- CIのゲートまで exit code を捨てると “fail closed” が壊れて長期的に破綻しやすい。
  （CIは従来通りでOK。ここは安全側に倒す。）

## Target Files (must be pinned)
- get_keywords_path: eval/run_eval.py
- stopwords_path: eval/run_eval.py (inline JAPANESE_STOPWORDS)

## Spec (proposed defaults)
### 1) long-hex exclusion
- token が `^[0-9a-fA-F]{40,}$` に一致したら除外（Git SHA-1(40)〜SHA256(64)をまとめて消す）
- ただし “普通の短いhex” (例: deadbeef) は残す（長さ閾値で守る）

### 2) half-width kana policy
- default: normalize (NFKC) を採用
  - 半角カナ → 全角へ正規化
  - 同一語の重複/揺れを潰す（RAG的に得）
- keep/drop を選ぶ場合は、理由を docs に1行残す

### 3) stopwords with reason
- TSV 形式に統一: `word<TAB>reason`
- loader は word だけを実際のstop判定に使い、reasonは監査ログとして残す

## Pseudocode
1) Discover & Pin Paths
   for each candidate in rg("def get_keywords("):
     if candidate contains "/tests/" then continue
     else choose first plausible (prefer src/, rag/, app/ など実装っぽい場所)
     break
   if none found:
     print("ERROR: get_keywords not found") and STOP (do not proceed)

   for each candidate in rg("stopwords" or known file names):
     choose canonical stopwords file
   if none found:
     print("ERROR: stopwords source not found") and STOP

2) Implement long-hex exclusion
   edit pinned get_keywords file:
     - token finalize直前に long-hex 判定を追加
     - match then skip
   run lightweight audit (single sample)
   if audit prints ERROR:
     STOP and record observation

3) Fix half-width kana policy
   if policy == "normalize":
     apply NFKC at earliest safe point (before tokenization)
   else if policy == "drop":
     remove half-width kana range tokens
   else:
     keep as-is
   ### 3) Stopwords Audit Trail
- **Policy**: Inline comments in `JAPANESE_STOPWORDS` (Python set).
- **Reason**: Simpler to maintain and audit within the code diff itself. External TSV was considered but deemed overkill for P3.
- **Format**: `"Word", # Reason` (ignore reason column)
   run lightweight audit
   if audit prints ERROR:
     STOP and record observation

5) Evidence
   - audit出力を “ログとして残す” (PR本文 or review bundle)
   - STATUS.md の S20-06 を 0→100% 更新
