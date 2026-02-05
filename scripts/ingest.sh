#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

mkdir -p "$root/logs" "$root/.run" "$root/data/inbox" "$root/data/raw"

ts="$(date +%Y%m%d-%H%M%S)"
log_main="$root/logs/ingest.log"
log_run="$root/logs/ingest.$ts.log"

# ロック（多重起動防止：macでも壊れにくいmkdirロック）
lock_dir="$root/.run/ingest.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "[ingest] ERROR: already running (lock exists): $lock_dir" >&2
  exit 2
fi
trap 'rmdir "$lock_dir" 2>/dev/null || true' EXIT

# ログ：標準出力/標準エラーを両方ファイルへ
exec > >(tee -a "$log_run" | tee -a "$log_main") 2>&1

echo "[ingest] start ts=$ts"
echo "[ingest] root=$root"
echo "[ingest] python=$(python3 --version 2>/dev/null || true)"

# 追加（inbox -> raw）
moved=0
shopt -s nullglob
for f in "$root/data/inbox/"*; do
  [[ -f "$f" ]] || continue
  name="$(basename "$f")"

  # 対象は md/txt のみ
  ext="${name##*.}"
  ext_lc="$(printf "%s" "$ext" | tr '[:upper:]' '[:lower:]')"
  if [[ "$ext_lc" != "md" && "$ext_lc" != "txt" ]]; then
    echo "[ingest] skip (unsupported ext): $name"
    continue
  fi

  dest="$root/data/raw/$name"
  if [[ -e "$dest" ]]; then
    dest="$root/data/raw/$name.$ts"
  fi

  # sha256（mac標準の shasum を使う）
  h="$(shasum -a 256 "$f" | awk '{print $1}')"
  echo "[ingest] add sha256=$h file=$name -> $(basename "$dest")"

  mv "$f" "$dest"
  moved=$((moved + 1))
done
echo "[ingest] moved=$moved"

# 再index
# 再index
echo "[ingest] build_index..."
python3 src/build_index.py

echo "[ingest] meta:"
if [[ -f "$root/index/meta.json" ]]; then
  cat "$root/index/meta.json"
  echo ""
else
  echo "[ingest] WARN: meta.json not found"
fi

# 簡易eval（失敗は失敗として返すが、ログは最後まで残す）
echo "[ingest] run_eval..."
set +e
python3 eval/run_eval.py
ec=$?
set -e

echo "[ingest] done eval_exit=$ec log=$log_run"
exit "$ec"
