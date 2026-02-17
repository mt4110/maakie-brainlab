# S20-05 TASK: Keyword Precision Tuning

## Step0: 観測（軽量）
- [x] `pwd` print
- [x] repo判定 (exit禁止)
- [x] 対象ファイルの追跡確認

## Step1: ブランチ開始（安全）
- [x] main最新化 (fail-safe)
- [x] 新規ブランチ: `s20-05-keyword-precision-v1`

## Step2: 仕様固定
- [x] `docs/ops/S20-05_PLAN.md` に仕様反映（Unicode, Stopwords, AlphaNum, Hiragana Exclusion）

## Step3: テスト追加
- [x] `tests/test_eval_logic.py` に `test_get_keywords_precision` 追加
    - CJK Ext-A/Compatible
    - Pure digit exclusion
    - Stopword filtering

## Step4: 実装
- [x] `eval/run_eval.py`: `get_keywords` regex update (Hiragana excluded)
- [x] `eval/run_eval.py`: Stopwords list add & filter logic
- [x] `eval/run_eval.py`: Digit strict filter

## Step5: 軽量検証
- [x] `unittest` (exit-safe runner)
- [x] Sample diff check (Implicit via tests)

## Step6: Docs
- [x] Verify `docs/ops/S20-05_PLAN.md` content
- [x] Mark `docs/ops/S20-05_TASK.md` complete

## Step7: reviewpack
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
