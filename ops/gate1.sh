#!/bin/bash
set -euo pipefail

# S4.4 Gate-1 Enforcement Script
# Validates invariants: Testing, Eval Success, Source Citation

echo "=== S4.4 Gate-1: The Constitution ==="

VERIFY_ONLY=0
if [[ "${1:-}" == "--verify-only" ]] || [[ "${GATE1_VERIFY_ONLY:-}" == "1" ]]; then
    VERIFY_ONLY=1
    echo "[Gate-1] Mode: Verify-Only (Skipping execution/env checks)"
fi

if [ "$VERIFY_ONLY" -eq 0 ]; then
    # 1. Pre-flight Checks (Environment)
    echo "[Gate-1] Checking environment..."
    python3 --version > /dev/null
    test -f eval/run_eval.py || { echo "[FAIL] eval/run_eval.py missing"; exit 1; }

    # Check symlinks (External Scope Boundary)
    for link in data index logs models; do
        if [ ! -L "$link" ]; then
            echo "[FAIL] '$link' must be a symlink to external storage."
            exit 1
        fi
    done
    echo "[OK] Environment check passed."

    # 2. Unit Tests (Functionality)
    echo "[Gate-1] Running Unit Tests..."
    if make test > /dev/null 2>&1; then
        echo "[OK] Unit tests passed."
    else
        echo "[FAIL] Unit tests failed. Check 'make test' output."
        exit 1
    fi

    # 3. Evaluation (Accuracy & Evidence)
    echo "[Gate-1] Running Evaluation..."
    if make run-eval > /dev/null 2>&1; then
        echo "[OK] Eval execution completed."
    else
        echo "[FAIL] Eval execution failed. Check 'make run-eval' output."
        exit 1
    fi
fi

# 4. Strict Verification (The "Constitution")
echo "[Gate-1] Verifying Eval Results (Pass + Sources)..."

# Find result file
LATEST_RESULT=""
if [ -f "eval/results/latest.jsonl" ]; then
    LATEST_RESULT="eval/results/latest.jsonl"
else
    # Lexicographical sort (LC_ALL=C) for determinism
    LATEST_RESULT=$(ls eval/results/*.jsonl 2>/dev/null | LC_ALL=C sort | tail -n1 || true)
fi

if [ -z "${LATEST_RESULT:-}" ]; then
  echo "[FAIL] No eval results found in eval/results/."
  exit 1
fi

echo "   Target result: $LATEST_RESULT"

python3 - "$LATEST_RESULT" <<'PY'
import sys, json

path = sys.argv[1]
failed = False

with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if not line.strip():
            continue
        rec = json.loads(line)

        # Skip meta line
        if rec.get("meta") == "pre_flight":
            continue

        qid = rec.get("id", "?")
        qtype = rec.get("type", "?")

        # 1) PASS check
        if rec.get("passed") is not True:
            print(f"[FAIL] Row {i}: passed=False (id={qid} type={qtype})")
            failed = True

        # 2) SOURCES check (exception for negative_control)
        details = rec.get("details") or {}
        has_sources = bool(details.get("has_sources"))

        if qtype == "negative_control":
            # Optional stronger rule:
            # if has_sources:
            #   print(f"[FAIL] Row {i}: negative_control must not have sources (id={qid})")
            #   failed = True
            continue

        if not has_sources:
            print(f"[FAIL] Row {i}: Missing sources (id={qid} type={qtype})")
            failed = True

if failed:
    sys.exit(1)

print("[OK] All records passed strict check.")
PY

echo "=== Gate-1 PASSED: System is Truthful & Verified ==="
