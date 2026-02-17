# S20-04 PLAN: Eval Wall v1 — Mixed Hallucination Hardening

## Goal
- negative_control の「unknown/不明と言いつつ余計な断言」を確実に FAIL にする
- failure_code は凍結リスト or null（UNKNOWN を出力しない）
- run_id の gitsha7 は 7桁（回帰防止）

## Scope
- eval/run_eval.py: unknown表記ゆれ + mixed hallucination 検出（negative_control強化）
- tests/test_eval_logic.py: 期待値を “嘘なし” に整合
- docs/ops/S20-04_TASK.md: CPU-safe 固定手順

## Pseudocode (Audit-grade)
try:
  observe eval/run_eval.py の unknown 判定（表記ゆれ）と negative_control 分岐
  observe tests/test_eval_logic.py の negative_control ケース
catch:
  error("観測できない: ファイル欠落/参照ズレ。進めない。見えている事実だけ報告して停止")

if unknown 判定が「分かりません/わかりません/不明/unknown」等を取りこぼす:
  try:
    unknown 判定に表記ゆれを追加（出力は UNKNOWN を使わず null or frozen code）
  catch:
    error("unknown 判定更新に失敗。進めないので停止")

else if negative_control が「unknown + 余計な断言」の混入を見逃す:
  try:
    for each line in answer_text:
      continue  # まず観測ログ（どの行が危険語を含むか）を作る
    detect mixed hallucination:
      - 結論が unknown 系なのに本文に断言語/一般論/追加説明が混入 -> POSITIVE_HALLUCINATION
  catch:
    error("mixed hallucination 検出の実装に失敗。停止")

else:
  continue  # 既に満たしている。回帰テストのみ足す

try:
  run light verify（python 単体テスト 1本）
catch:
  error("軽い検証が失敗。停止してログを貼る")

try:
  run heavy gates（最後にまとめて nice）
catch:
  error("ゲート失敗。停止してコマンド+出力を貼る")
