# S20-06(P3) TASK — Keyword Noise Guardrails

## 0) Preflight (軽量)
- [ ] repo ルートへ移動（失敗してもexitしない）
  - `cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "ERROR: not in git repo"`
- [ ] 現在のブランチと差分確認（観測だけ）
  - `git status -sb 2>/dev/null || echo "ERROR: git status failed"`

## 1) ブランチ作成（観測→実行）
- [ ] main最新化（失敗しても止めない。出力を見て判断）
  - `git switch main 2>/dev/null || echo "ERROR: git switch main failed"`
  - `git pull --ff-only 2>/dev/null || echo "ERROR: git pull failed"`
- [ ] 作業ブランチ作成
  - `git switch -c s20-06-keyword-noise-guardrails-v1 2>/dev/null || echo "ERROR: branch create failed"`

## 2) get_keywords 実体パスを “1つに固定” （ここが最重要）
- [ ] 候補ファイル列挙（tests除外で探索）
  - `rg -n --files-with-matches 'def get_keywords\(' . 2>/dev/null | rg -v '/tests?/' || echo "ERROR: no candidates"`
- [ ] 1つ選んで PLAN に固定（手で追記）
  - ルール: 実装っぽい場所（src/, rag/, app/ など）を優先。複数あるなら “実際に呼ばれてる方”。
  - PLAN の `Target Files` に `get_keywords_path: <path>` を追記。

## 3) stopwords ソースのパスも固定
- [ ] stopwords候補探索（ファイル名/参照から）
  - `rg -n 'stopwords' . 2>/dev/null | head -n 50 || echo "ERROR: stopwords refs not found"`
  - `rg -n --files-with-matches 'stopwords' . 2>/dev/null | head -n 50 || echo "ERROR: stopwords file scan empty"`
- [ ] 1つ選んで PLAN に固定（手で追記）
  - PLAN の `Target Files` に `stopwords_path: <path>` を追記。

## 4) long-hex 除外を実装（最小差分）
- [ ] get_keywords の token finalize 直前に追加（helper関数は作らずインラインでOK）
  - spec: `^[0-9a-fA-F]{40,}$` は除外
- [ ] 変更点を git diff で観測
  - `git diff -- . 2>/dev/null || echo "ERROR: git diff failed"`

## 5) 半角カナ方針を固定（default: normalize/NFKC）
- [ ] get_keywords の “トークン化前” の安全地点で NFKC 正規化を適用
  - normalize採用理由: 揺れを潰して重複を減らす（RAG的に得）
- [ ] PLAN の `half-width kana policy` を “normalize” に確定（理由1行も書く）

## 6) stopwords を TSV(reason付き) へ移行
- [ ] stopwordsファイルを `word<TAB>reason` 形式へ（理由は1行ずつ）
- [ ] loader を TSV 対応に更新
  - 実動: word列のみ使用
  - 監査: reason列は保持（コメント/空行はSKIP扱い）

## 7) 軽量監査（exitに依存しない）
- [ ] `scripts/keyword_audit.py` を追加（例外は握って print、プロセスは落とさない）
  - 入力例に以下を含める:
    - SHA256っぽい64hex
    - Git SHAっぽい40hex
    - 半角カナ混在文
    - stopwordsっぽい語
  - 出力に `OK:` / `ERROR:` / `SKIP:` を必ず含める
- [ ] 実行（失敗しても次に進まない判断は “人間が” する）
  - `python3 scripts/keyword_audit.py 2>/dev/null || echo "ERROR: audit crashed (see output)"`

## 8) STATUS 更新（0→100%）
- [ ] STATUS のパス探索（見つけたら break）
  - `for p in docs/ops/STATUS.md docs/STATUS.md STATUS.md; do if [ -f "$p" ]; then echo "OK: STATUS=$p"; break; else echo "SKIP: not found $p"; fi; done`
- [ ] 見つけた STATUS を更新
  - S20-06 を追加 or 既存行の % / Current / Last Updated を更新
  - このPR完了時: S20-06 100%

## 9) Commit（小さく分割）
- [ ] commit1: docs(ops) add S20-06 plan/task
- [ ] commit2: feat(keywords) long-hex exclusion
- [ ] commit3: feat(keywords) half-width kana policy fixed
- [ ] commit4: feat(keywords) stopwords reason TSV + loader
- [ ] commit5: chore(audit) add scripts/keyword_audit.py
- [ ] commit6: docs(ops) update STATUS S20-06 100%

## 10) 仕上げ観測
- [ ] `git status -sb` が clean を確認
- [ ] `git diff main...HEAD` を観測して過剰変更がないか確認
