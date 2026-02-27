# S22-08 (P8): Eval Wall v2 (IL-centered) — TASK (Ambi-safe)

## 0) 絶対ルール
- exit/return非0/set -e/trap EXIT 禁止
- STOP フラグで止める（次へ進まない）
- 重い処理は limit/timebox で分割
- ログは OBS に保存（監査可能）

---

## 1) Kickoff: 観測ディレクトリを作る（軽い）
- [x] OBS作成
```bash
bash -lc '
cd "/Users/takemuramasaki/dev/maakie-brainlab" 2>/dev/null || true
TS="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
OBS=".local/obs/s22-08_01_kickoff_${TS}"
mkdir -p "$OBS" 2>/dev/null || true
echo "OK: obs_dir=$OBS"
git rev-parse HEAD 2>/dev/null | tee "$OBS/10_head_sha.txt" >/dev/null || true
python3 -V 2>/dev/null | tee "$OBS/11_python_ver.txt" >/dev/null || true
echo "OK: done"
'
```

---

## 2) Dataset 探索（for/continue/break で “確実に見つける”）

- [x] data/eval/datasets を観測
```bash
bash -lc '
cd "/Users/takemuramasaki/dev/maakie-brainlab" 2>/dev/null || true
TS="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
OBS=".local/obs/s22-08_02_find_${TS}"
mkdir -p "$OBS" 2>/dev/null || true

echo "== ls datasets ==" | tee "$OBS/10_header_ls.txt"
ls -la data/eval/datasets 2>&1 | tee "$OBS/11_ls.log" || true

echo "== candidates ==" | tee "$OBS/20_header_candidates.txt"
find data/eval/datasets -maxdepth 4 -type f \( -name "*.jsonl" -o -name "*.json" \) 2>&1 | tee "$OBS/21_find.log" || true

echo "OK: done"
'
```

- [x] 候補を 1つに確定（手動で DATASET_FILE に貼る：嘘を入れない）
```bash
bash -lc '
cd "/Users/takemuramasaki/dev/maakie-brainlab" 2>/dev/null || true
STOP="0"

TS="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
OBS=".local/obs/s22-08_03_pick_${TS}"
mkdir -p "$OBS" 2>/dev/null || true

DATASET_FILE=""  # ← obs(02_find) の結果から “実在する1本” をコピペで入れる

if [ -z "$DATASET_FILE" ]; then
  echo "ERROR: set DATASET_FILE from obs(s22-08_02_find)" | tee "$OBS/10_error_need_dataset.txt"
  STOP="1"
else
  if [ -f "$DATASET_FILE" ]; then
    echo "OK: dataset_file=$DATASET_FILE" | tee "$OBS/11_ok_dataset_path.txt"
  else
    echo "ERROR: dataset_file_missing path=$DATASET_FILE" | tee "$OBS/12_error_missing.txt"
    STOP="1"
  fi
fi

if [ "$STOP" = "0" ]; then
  echo "== head (schema glimpse) ==" | tee "$OBS/20_header_head.txt"
  head -n 3 "$DATASET_FILE" 2>&1 | tee "$OBS/21_head.log" || true

  echo "== sha256 (python stopless) ==" | tee "$OBS/30_header_sha.txt"
  python3 - <<'PY' 2>&1 | tee "$OBS/31_sha.log" >/dev/null || true
import hashlib, sys
p = "${DATASET_FILE}"
try:
  h = hashlib.sha256()
  with open(p, "rb") as f:
    for b in iter(lambda: f.read(1024*1024), b""):
      h.update(b)
  print("OK: dataset_sha256=" + h.hexdigest())
except Exception as e:
  print("ERROR: sha256_failed err=" + e.__class__.__name__)
PY
fi

echo "OK: done stop=$STOP"
'
```

---

## 3) ランナー実装（新規ファイル1本。軽い）

- [x] scripts/eval_wall_v2_il_centered.py を作成/更新

仕様（最低限）：
- 引数：--dataset --out --mode --offset --limit --resume --timebox-sec
- 1ケースごとに result.json を必ず出す（OK/ERROR/SKIP）
- 例外は catch して ERROR として記録（traceback を stdout に撒かない）
- run.json は “追記型”（segments[] を append）で壊れない

---

## 4) Smoke（validate-only / 低負荷）

- [x] limit=5 timebox=20 でまず通す
```bash
bash -lc '
cd "/Users/takemuramasaki/dev/maakie-brainlab" 2>/dev/null || true
STOP="0"

TS="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
OBS=".local/obs/s22-08_04_smoke_validate_${TS}"
OUT=".local/out/eval/s22-08_smoke_${TS}"
mkdir -p "$OBS" "$OUT" 2>/dev/null || true

DATASET_FILE=""  # ← 03_pick と同じものを貼る

if [ -z "$DATASET_FILE" ]; then
  echo "ERROR: set DATASET_FILE" | tee "$OBS/10_error_need_dataset.txt"
  STOP="1"
fi

if [ "$STOP" = "0" ]; then
  echo "== run ==" | tee "$OBS/20_header_run.txt"
  (python3 scripts/eval_wall_v2_il_centered.py \
    --dataset "$DATASET_FILE" \
    --out "$OUT" \
    --mode validate-only \
    --offset 0 \
    --limit 5 \
    --resume \
    --timebox-sec 20 2>&1 || true) | tee "$OBS/21_run.log" >/dev/null

  echo "== outputs check ==" | tee "$OBS/30_header_check.txt"
  ls -la "$OUT" 2>&1 | tee "$OBS/31_ls_out.log" || true
  test -f "$OUT/summary.json" && echo "OK: summary_exists" | tee "$OBS/32_ok_summary.txt" || echo "ERROR: summary_missing" | tee "$OBS/33_error_summary.txt"
fi

echo "OK: done stop=$STOP"
'
```

---

## 5) Smoke（validate-exec / さらに軽く：1件だけ）

- [x] validate-exec は “1件だけ” で様子見（CPUが跳ねるならここで止める）
```bash
bash -lc '
cd "/Users/takemuramasaki/dev/maakie-brainlab" 2>/dev/null || true
STOP="0"

TS="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
OBS=".local/obs/s22-08_05_smoke_exec_${TS}"
OUT=".local/out/eval/s22-08_exec_smoke_${TS}"
mkdir -p "$OBS" "$OUT" 2>/dev/null || true

DATASET_FILE=""  # ←同上

if [ -z "$DATASET_FILE" ]; then
  echo "ERROR: set DATASET_FILE" | tee "$OBS/10_error_need_dataset.txt"
  STOP="1"
fi

if [ "$STOP" = "0" ]; then
  echo "== run exec(1 case) ==" | tee "$OBS/20_header_run.txt"
  (python3 scripts/eval_wall_v2_il_centered.py \
    --dataset "$DATASET_FILE" \
    --out "$OUT" \
    --mode validate-exec \
    --offset 0 \
    --limit 1 \
    --resume \
    --timebox-sec 20 2>&1 || true) | tee "$OBS/21_run.log" >/dev/null
fi

echo "OK: done stop=$STOP"
'
```

---

## 6) 分割本走（20件ずつ。固まるなら 10件ずつ）

- [x] 20件ずつ segment 実行（同一 OUT に resume で積む）
```bash
bash -lc '
cd "/Users/takemuramasaki/dev/maakie-brainlab" 2>/dev/null || true
STOP="0"

TS="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
OBS=".local/obs/s22-08_06_segments_${TS}"
OUT=".local/out/eval/s22-08_run_${TS}"
mkdir -p "$OBS" "$OUT" 2>/dev/null || true

DATASET_FILE=""  # ←同上
MODE="validate-only"  # まずは安全側。execは後で

if [ -z "$DATASET_FILE" ]; then
  echo "ERROR: set DATASET_FILE" | tee "$OBS/10_error_need_dataset.txt"
  STOP="1"
fi

# 分割設定（軽い）
OFFSETS="0 20 40 60 80"
LIMIT="20"
TBOX="30"

if [ "$STOP" = "0" ]; then
  echo "OK: out_dir=$OUT" | tee "$OBS/11_ok_out.txt"
  echo "OK: offsets=$OFFSETS limit=$LIMIT timebox=$TBOX mode=$MODE" | tee "$OBS/12_ok_plan.txt"
fi

if [ "$STOP" = "0" ]; then
  for off in $OFFSETS; do
    echo "== segment off=$off ==" | tee "$OBS/20_header_seg_${off}.txt"
    (python3 scripts/eval_wall_v2_il_centered.py \
      --dataset "$DATASET_FILE" \
      --out "$OUT" \
      --mode "$MODE" \
      --offset "$off" \
      --limit "$LIMIT" \
      --resume \
      --timebox-sec "$TBOX" 2>&1 || true) | tee "$OBS/21_seg_${off}.log" >/dev/null
    echo "OK: segment_done off=$off" | tee "$OBS/22_ok_seg_${off}.txt"
  done
fi

echo "OK: done stop=$STOP"
'
```

---

## 7) Docs/SOT 更新（STATUS + Plan/Task）

- [x] docs/ops/STATUS.md に S22-08 を WIP で追加し、進捗%を書く（例：5%）
- [x] docs/ops/S22-08_PLAN.md / TASK.md を含めてコミット

---

## 8) verify-only（証拠の束）

- [x] 既存の reviewpack 流儀で verify-only → bundle sha256 を OBS に保存
- [x] “PASS判定はログ文字列” で行い、exitに依存しない

---

## 9) PR 作成〜マージ（1PRで閉じ切る）

- [x] milestone: S22-08
- [x] merge は ops/pr_merge_guard.sh（dry→execute）
- [x] gh pr view --json mergedAt,mergeCommit で事後確認（merged フィールド禁止）


## Extension: 6-10%% Pack
- [x] Rebuild without dataset
- [x] Corruption Drill (RESULT_SCHEMA mismatch)
- [x] Verify-only bundle evidence
