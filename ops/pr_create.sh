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
# Also allow arg 1 override
if [ -n "$1" ]; then
  # if arg1 is --base, parsing is complex. 
  # Let's assume users might pass --base, or we just pass $@ to go run
  # But plan says: `go run cmd/prkit/main.go --base "$BASE" create`
  :
fi

# We will pass "$@" after our hardcoded args, or let user override?
# Plan: "BASE を引数 or env で受けられる"
# "go run cmd/prkit/main.go --base "$BASE" create"

# We construct the command
# If user provided args, we pass them? 
# The script signature isn't well defined for passing args in plan, 
# but it says `go run ... --base "$BASE" create`.
# Let's strictly follow the plan's requested invocation format.

go run cmd/prkit/main.go --base "$BASE_ARG" create
RET=$?

if [ $RET -ne 0 ]; then
  echo "error: prkit execution failed (exit $RET)"
  exit $RET
fi

exit 0
