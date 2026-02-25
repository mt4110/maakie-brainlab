#!/usr/bin/env python3
"""
S22-14: Always-on guard to ensure Canonical Entrypoint is used for IL execution.
"""
import subprocess
from pathlib import Path

CANONICAL_ENTRYPOINT = "scripts/il_entry.py"

def main():
    repo_root = Path(__file__).resolve().parent.parent
    try:
        # Search for legacy entrypoint invocations in key directories
        cmd = [
            "rg", "--no-heading", "--line-number", "--color", "never",
            r"(python3?\s+.*scripts/il_(?:exec|check|guard|exec_run)\.py)",
            "Makefile", "ops", ".github", "docs/ops"
        ]
        
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        
        errors_found = 0
        if result.stdout:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                print(f"ERROR: non-canonical entrypoint reference: {line}")
                print(f"::error::non-canonical entrypoint reference: {line}")
                errors_found += 1
                
        if errors_found == 0:
            print(f"OK: all entrypoint references are canonical ({CANONICAL_ENTRYPOINT}).")
            
    except Exception as e:
        print(f"ERROR: unexpected error in guard: {e}")

if __name__ == "__main__":
    main()
