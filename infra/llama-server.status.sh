#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "$root/infra/llama-server.env"

pid_file="$root/.run/llama-server.pid"
log_file="$root/logs/llama-server.log"
url="http://$LLAMA_HOST:$LLAMA_PORT/v1/models"

if [[ -f "$pid_file" ]]; then
  pid="$(cat "$pid_file" || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "[llama-server] RUNNING pid=$pid"
    echo "health: $url"
    echo "log   : $log_file"
    exit 0
  fi
fi

echo "[llama-server] STOPPED"
echo "log: $log_file"
exit 1
