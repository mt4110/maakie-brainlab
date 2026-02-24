# S22-08 (P8): Eval Wall v2 (IL-centered) — PLAN (Ambi-safe)

## Goal
IL Single Entry（scripts/il_entry.py）を唯一の入口として、
Eval Wall を **IL-centered** に再配置し、改善を「計測」で語れる状態にする。

## Absolute Rules (Must)
- exit 系全面禁止（シェル: exit/return非0/set -e/trap EXIT 等 / Python: sys.exit/SystemExit/assert 禁止）
- 失敗でプロセス停止を設計に持ち込まない（判定は出力テキストと STOP フラグ）
- CPU負荷が上がる処理は **分割**（1ステップ1本、limit/timebox で短く切る）
- stdout は最小（OK/ERROR/SKIP と要約）。詳細は out/obs へ。

## Inputs / SOT
- Entry: scripts/il_entry.py
- Dataset root: data/eval/datasets/
- Dataset file: 探索して 1つに固定（OBSで証拠化）
- Output:
  - OBS: .local/obs/s22-08_* （観測ログ）
  - OUT: .local/out/eval/s22-08_* （成果物）

## Outputs (Artifacts)
OUT/run.json
- repo_head_sha, python_version, dataset_path, dataset_sha256
- mode (validate-only / validate-exec)
- segments[] (offset, limit, timebox_sec, started_at_utc, ended_at_utc)

OUT/cases/<case_id>/result.json
- status: OK|ERROR|SKIP
- error_code (best-effort)
- entry_args (used)
- durations_ms (best-effort)

OUT/summary.json
- total / ok / error / skip
- breakdown_by_error_code
- validation_fail_count / execution_fail_count (best-effort)

OUT/SHA256SUMS.txt
- run.json / summary.json ほか重要ファイルの sha256

## Core Design (Working Theory)
- “計測”の最小核は **OK/ERROR/SKIP の三値**。これを壊さずに積み上げる。
- v2 は「指標の増加」より「測定系の安定（再現性・監査可能性）」を優先する。

## Stopless Algorithm (Pseudo)
STOP = 0

# Phase A: Discover dataset (light)
if not in repo:
  error("ERROR: not in repo"); STOP=1
else:
  candidates = discover dataset files under data/eval/datasets
  for c in candidates:
    if exists(c) and looks_like_jsonl(c):
      DATASET_FILE = c
      break
    else:
      continue
  if DATASET_FILE empty:
    error("ERROR: dataset not found"); STOP=1

# Phase B: Prepare out/obs
if STOP==0:
  ensure OUT, OBS
  try:
    dataset_sha256 = sha256(DATASET_FILE)
  catch:
    error("ERROR: cannot sha256 dataset"); STOP=1

# Phase C: Segment runs (CPU-safe)
# - small smoke first: limit=5 timebox_sec=20
# - then segmented: (offset,limit) = (0,20),(20,20)... ; timebox_sec short
if STOP==0:
  SEGMENTS = [(0,5,20)] + planned_segments()
  for seg in SEGMENTS:
    if STOP!=0:
      break

    try:
      run_segment(seg):
        - loop cases from offset..offset+limit
        - for each case:
            if resume && result exists: write SKIP(already_done); continue
            try:
              call scripts/il_entry.py with --out case_dir
              parse stdout -> status + error_code
              write result.json
            catch:
              write ERROR result.json (no traceback spam)
              continue
            if timebox exceeded:
              write SKIP(timebox_exceeded) and break segment loop
        - update run.json append segment record
        - aggregate summary.json (incremental; stable)
    catch:
      # segment-level catch: never kill the process
      write OBS error + continue next segment
      continue

# Phase D: Integrity
if STOP==0:
  write SHA256SUMS.txt
  print OK summary totals
else:
  print ERROR: stopped (see OBS)

## CPU / Freeze Prevention (重要)
- デフォルトは小さく：limit=5, timebox_sec=20
- “本走”は 20件ずつ分割。固まりそうなら limit=10 に落とす。
- 並列はしない。
- timebox を必ず入れ、1回の実行が長時間化しないようにする。

## DoD
- scripts/eval_wall_v2_il_centered.py が stopless に動作
- smoke (limit=5) で summary.json が出る
- 分割実行 + resume で積み上げ可能
- run.json / summary.json / SHA256SUMS.txt が揃う
- verify-only PASS の bundle sha256 を PR Evidence に固定
