#!/bin/bash
set -e

# Resolve repo root
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ ! -f "cmd/prkit/main.go" ]; then
  echo "error: cmd/prkit/main.go not found"
  exit 1
fi

# Run the tool
go run cmd/prkit/main.go create "$@"
