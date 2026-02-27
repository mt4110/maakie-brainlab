#!/bin/bash
# pr_create.sh - Safe wrapper for prkit
# No set -e (handle errors explicitly)

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
  echo "error: not a git repo"
  exit 1
fi

cd "$ROOT"

if [ ! -f "cmd/prkit/main.go" ]; then
  echo "error: cmd/prkit/main.go not found"
  exit 1
fi

BASE_ARG="main"
if [ -n "$BASE" ]; then
  BASE_ARG="$BASE"
fi

go run cmd/prkit/main.go --base "$BASE_ARG" create
RET=$?

if [ $RET -ne 0 ]; then
  echo "error: prkit execution failed (exit $RET)"
  exit $RET
fi

exit 0
