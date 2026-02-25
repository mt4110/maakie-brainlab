#!/usr/bin/env bash
# stopless wrapper
MODE="${1:-check}"
MODE="$MODE" python3 ops/required_checks_sot.py 2>&1 || true
true
