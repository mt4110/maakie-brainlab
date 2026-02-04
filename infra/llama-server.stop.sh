cat >infra/llama-server.stop.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
pid_file="$root/.run/llama-server.pid"
log_file="$root/logs/llama-server.log"

if [[ ! -f "$pid_file" ]]; then
  echo "[llama-server] not running (no pid file)"
  exit 0
fi

pid="$(cat "$pid_file" || true)"
if [[ -z "${pid:-}" ]]; then
  echo "[llama-server] not running (empty pid file)"
  rm -f "$pid_file"
  exit 0
fi

if ! kill -0 "$pid" 2>/dev/null; then
  echo "[llama-server] not running (stale pid=$pid)"
  rm -f "$pid_file"
  exit 0
fi

echo "[llama-server] stopping pid=$pid ..."
kill "$pid" 2>/dev/null || true

# 最大10秒待つ
for _ in {1..100}; do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pid_file"
    echo "[llama-server] stopped"
    exit 0
  fi
  sleep 0.1
done

echo "[llama-server] still alive, SIGKILL..."
kill -9 "$pid" 2>/dev/null || true
rm -f "$pid_file"
echo "[llama-server] killed"
echo "log: $log_file"
EOF

chmod +x infra/llama-server.stop.sh
