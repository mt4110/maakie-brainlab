#!/bin/bash
set -euo pipefail

# ops/seed_eval_results.sh
# Purpose: Seed eval/results/ci.jsonl & latest.jsonl from fixtures for local verify-only.

# Input: Fixture
FIX="eval/fixtures/latest.jsonl"
if [ ! -f "$FIX" ]; then
    echo "[FAIL] Missing fixture: $FIX"
    exit 1
fi

# Ensure directory exists
mkdir -p eval/results

# Seed ci.jsonl (if missing)
if [ ! -f eval/results/ci.jsonl ]; then
    cp -f "$FIX" eval/results/ci.jsonl
    echo "[OK] Seeded eval/results/ci.jsonl"
else
    echo "[OK] eval/results/ci.jsonl already exists"
fi

# Seed latest.jsonl (if missing)
if [ ! -f eval/results/latest.jsonl ]; then
    cp -f "$FIX" eval/results/latest.jsonl
    echo "[OK] Seeded eval/results/latest.jsonl"
else
    echo "[OK] eval/results/latest.jsonl already exists"
fi

# Show result
ls -la eval/results
