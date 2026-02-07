#!/bin/bash
set -euo pipefail

# S4.4 Gate-1 Enforcement Script
# Validates invariants: Testing, Eval Success, Source Citation

echo "=== S4.4 Gate-1: The Constitution ==="

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
# Run eval (using existing Makefile target if possible, or direct)
# We use make run-eval to ensure consistency
if make run-eval > /dev/null 2>&1; then
    echo "[OK] Eval execution completed."
else
    echo "[FAIL] Eval execution failed. Check 'make run-eval' output."
    exit 1
fi

# 4. Strict Verification (The "Constitution")
echo "[Gate-1] Verifying Eval Results (Pass + Sources)..."

# Find latest result file (by mtime)
LATEST_RESULT=$(ls -t eval/results/eval_*.jsonl 2>/dev/null | head -n1)

if [ -z "$LATEST_RESULT" ]; then
    echo "[FAIL] No eval results found in eval/results/."
    exit 1
fi

echo "   Latest result: $LATEST_RESULT"

# Verify Content:
# 1. pass must be true
# 2. sources must not be empty (list) or null
python3 - <<EOF
import sys
import json

path = "$LATEST_RESULT"
failed = False

try:
    with open(path) as f:
        for i, line in enumerate(f, 1):
            if not line.strip(): continue
            record = json.loads(line)
            
            # Check PASS
            if not record.get("pass", False):
                print(f"[FAIL] Row {i}: pass=False (Question: {record.get('question_id', '?')})")
                failed = True
                
            # Check SOURCES (Must be present and non-empty list)
            sources = record.get("sources", [])
            if not sources or not isinstance(sources, list):
                 # Check for explicit exception tag if we had one, but strict rule says NO by default
                 # For now, Gate-1 mandates sources for ALL answers in this pipeline.
                 print(f"[FAIL] Row {i}: Missing sources (Question: {record.get('question_id', '?')})")
                 failed = True

except Exception as e:
    print(f"[FAIL] Error parsing result file: {e}")
    sys.exit(1)

if failed:
    sys.exit(1)
print("[OK] All records passed strict check.")
EOF

echo "=== Gate-1 PASSED: System is Truthful & Verified ==="
