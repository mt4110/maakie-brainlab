#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${1:-}"
if [[ -z "${MODEL_PATH}" ]]; then
  echo "usage: ./infra/run-llama-server.sh /path/to/model.gguf [port]" >&2
  exit 2
fi
PORT="${2:-${LLAMA_SERVER_PORT:-11434}}"

# llama.cpp installed via brew (recommended first step)
# server: OpenAI-compatible API at http://127.0.0.1:${PORT}/v1
#exec llama-server -m "${MODEL_PATH}" --host 127.0.0.1 --port "${PORT}" -c 4096
exec llama-server -m "${MODEL_PATH}" --host 127.0.0.1 --port "${PORT}" -c 4096 -ngl 999
