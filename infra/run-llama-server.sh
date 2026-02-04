#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${1:-}"
if [[ -z "${MODEL_PATH}" ]]; then
  echo "usage: ./infra/run-llama-server.sh /path/to/model.gguf" >&2
  exit 2
fi

# llama.cpp installed via brew (recommended first step)
# server: OpenAI-compatible API at http://127.0.0.1:8080/v1
#exec llama-server -m "${MODEL_PATH}" --host 127.0.0.1 --port 8080 -c 4096
exec llama-server -m "${MODEL_PATH}" --host 127.0.0.1 --port 8080 -c 4096 -ngl 999

