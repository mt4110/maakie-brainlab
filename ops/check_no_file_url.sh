#!/bin/bash
set -euo pipefail

# ops/check_no_file_url.sh
# Checks for accidental `file://` links in documentation and key artifacts.
#
# Rules:
# 1. Deny markdown links: `](file://`
# 2. Deny autolinks: `<file://`
# 3. Allow text examples: `file://` (when not part of a link structure)

# Files to check
TARGETS=(
    "docs"
    "walkthrough.md"
    "task.md"
    "implementation_plan.md"
)

# Convert arrays to find args if needed, or just pass to grep
# We use grep -r for directories and files directly.

# Pattern explanation:
# - `\]\(file://` : Matches markdown link target starting with file://
# - `<file://`    : Matches autolink starting with file://

echo "[CHECK] Scanning for forbidden file:// links..."

FOUND=0

# Use grep with line numbers and recursive for directories
# We use extended regex (-E)
# Note: we need to handle potential absence of files gracefully, but robustly.

for target in "${TARGETS[@]}"; do
    if [ -e "$target" ]; then
        if grep -r -n -E '\]\(file://|<file://' "$target"; then
            echo "[FAIL] Found forbidden file:// link in $target"
            FOUND=1
        fi
    else
        # It's okay if a target doesn't exist (e.g. no docs dir yet), but warn.
        # implementation_plan.md and task.md SHOULD exist.
        if [[ "$target" == "task.md" || "$target" == "implementation_plan.md" ]]; then
             echo "[WARN] Required artifact missing: $target"
        fi
    fi
done

if [ "$FOUND" -eq 1 ]; then
    echo ""
    echo "[ERROR] 'file://' links detected!"
    echo "       Please remove them or convert to relative paths."
    echo "       See docs/ops/IF_FAIL_C10.md for details."
    exit 1
else
    echo "[OK] No forbidden file:// links found."
    exit 0
fi
