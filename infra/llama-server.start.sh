#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

# shellcheck source=/dev/null
source "$root/infra/llama-server.env"

mkdir -p "$root/logs" "$root/.run"

pid_file="$root/.run/llama-server.pid"
log_file="$root/logs/llama-server.log"

if [[ -f "$pid_file" ]]; then
  pid="$(cat "$pid_file" || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "[llama-server] already running: pid=$pid"
    echo "log: $log_file"
    exit 0
  fi
fi

# 最終フォールバック（PATH薄い事故に強い）
if [[ ! -x "${LLAMA_SERVER_BIN:-}" ]]; then
  for cand in \
    "/opt/homebrew/bin/llama-server" \
    "/usr/local/bin/llama-server" \
    "$(command -v llama-server 2>/dev/null || true)"; do
    if [[ -n "${cand:-}" ]] && [[ -x "$cand" ]]; then
      LLAMA_SERVER_BIN="$cand"
      break
    fi
  done
fi

if [[ ! -x "$LLAMA_SERVER_BIN" ]]; then
  echo "[llama-server] ERROR: LLAMA_SERVER_BIN not found or not executable: $LLAMA_SERVER_BIN" >&2
  exit 1
fi
if [[ ! -f "$LLAMA_MODEL" ]]; then
  echo "[llama-server] ERROR: model not found: $LLAMA_MODEL" >&2
  exit 1
fi

# ログ肥大の簡易ガード（200MB超えたら退避）
if [[ -f "$log_file" ]]; then
  size_bytes="$(wc -c <"$log_file" | tr -d ' ')"
  if [[ "$size_bytes" -ge 200000000 ]]; then
    ts="$(date +%Y%m%d-%H%M%S)"
    mv "$log_file" "$root/logs/llama-server.$ts.log"
  fi
fi

echo "[llama-server] starting..."
echo "bin : $LLAMA_SERVER_BIN"
echo "model: $LLAMA_MODEL"
echo "bind: http://$LLAMA_HOST:$LLAMA_PORT"
echo "log : $log_file"

nohup "$LLAMA_SERVER_BIN" \
  -m "$LLAMA_MODEL" \
  --host "$LLAMA_HOST" \
  --port "$LLAMA_PORT" \
  -c "$LLAMA_CTX" \
  -ngl "$LLAMA_NGL" \
  $LLAMA_EXTRA_ARGS \
  >>"$log_file" 2>&1 &

pid="$!"
echo "$pid" >"$pid_file"

sleep 0.2
if kill -0 "$pid" 2>/dev/null; then
  echo "[llama-server] OK pid=$pid"
else
  echo "[llama-server] ERROR: failed to start. see log: $log_file" >&2
  exit 1
fi
