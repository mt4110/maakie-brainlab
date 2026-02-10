#!/bin/bash
# ops/finalize_clean.sh
# Detect and Fix forbidden patterns (AI Text Guard)
# Usage: bash ops/finalize_clean.sh [--check|--fix]

set -euo pipefail

MODE="${1:---check}"

# Construct forbidden pattern strings to avoid self-detection
# We want to detect "file" + "://"
# But we must NOT write that sequence literally in this script.
# We replace it with "file[:]//"
PAT_PROTO="file"
PAT_SEP="://"
FORBIDDEN_SEQ="${PAT_PROTO}${PAT_SEP}"

# Safe replacement
SAFE_REPLACEMENT="${PAT_PROTO}[:]//"

# Targets to scan
# We focus on docs, .github, README.md, ops, scripts, prompts
TARGETS=(docs .github README.md ops scripts prompts)

check_files() {
    echo "[CHECK] Scanning for forbidden '${FORBIDDEN_SEQ}' patterns..."
    
    # Use rg if available, else grep
    # We purposefully break the pattern in the command line args if using grep/rg
    # patterns are constructed via variables so the command line itself is safe(ish) 
    # but strictly speaking, we pass the forbidden sequence as a regex.
    
    # However, since this script ITSELF is in 'ops/', it will scan itself.
    # We must ensure WE don't contain the forbidden sequence.
    # We already constructed it via vars, so the literal string isn't here.
    
    local found=0
    
    # We use 'rg' or 'grep' to find the sequence.
    # Exclude .git and pre-commit hook itself if needed (though .githooks usually outside scan target dirs if not specified)
    # But 'ops' is in TARGETS.
    
    if command -v rg >/dev/null 2>&1; then
        # rg is faster
        if rg -n "${FORBIDDEN_SEQ}" "${TARGETS[@]}" 2>/dev/null; then
            found=1
        fi
    else
        # Fallback to grep
        if grep -r -n "${FORBIDDEN_SEQ}" "${TARGETS[@]}" 2>/dev/null; then
            found=1
        fi
    fi
    
    if [ "$found" -eq 1 ]; then
        echo "[FAIL] Forbidden patterns found!"
        return 1
    else
        echo "[PASS] No forbidden patterns found."
        return 0
    fi
}

fix_files() {
    echo "[FIX] Auto-fixing forbidden patterns..."
    
    # Find files containing the pattern
    # We use grep -l to list them
    local file_list
    file_list=$(grep -r -l "${FORBIDDEN_SEQ}" "${TARGETS[@]}" 2>/dev/null || true)
    
    if [ -z "$file_list" ]; then
        echo "[INFO] Nothing to fix."
        return 0
    fi
    
    # Iterate and replace
    # Using sed. Note checking for OS (macOS vs Linux) for -i
    # macOS sed requires -i '', Linux sed requires -i
    
    for f in $file_list; do
        if [ -f "$f" ]; then
            echo "Fixing: $f"
            # Use perl for cross-platform in-place editing if available, it's more reliable than sed -i portability
            if command -v perl >/dev/null 2>&1; then
                perl -pi -e "s|${FORBIDDEN_SEQ}|${SAFE_REPLACEMENT}|g" "$f"
            else
                # Fallback to sed (assume linux/gnu sed behavior or try generic)
                # Try logic for mac vs linux
                if [[ "$OSTYPE" == "darwin"* ]]; then
                     sed -i '' "s|${FORBIDDEN_SEQ}|${SAFE_REPLACEMENT}|g" "$f"
                else
                     sed -i "s|${FORBIDDEN_SEQ}|${SAFE_REPLACEMENT}|g" "$f"
                fi
            fi
        fi
    done
    
    echo "[INFO] Fix complete. Showing diff:"
    git diff -- "${TARGETS[@]}" || true
}

sanity_check_self() {
    # Ensure this script doesn't contain the pattern literally (double check)
    # We use the variable ${FORBIDDEN_SEQ} to check, but we must ensure we don't write the literal string in grep
    if grep -q "${PAT_PROTO}${PAT_SEP}" "$0"; then
         echo "[CRITICAL] Script contains forbidden pattern check logic incorrectly! Fix script."
         exit 99
    fi
}

sanity_check_self

if [ "$MODE" == "--fix" ]; then
    fix_files
    # Verify after fix
    check_files
elif [ "$MODE" == "--check" ]; then
    check_files
else
    echo "Usage: $0 [--check|--fix]"
    exit 1
fi
