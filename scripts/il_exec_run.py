#!/usr/bin/env python3
"""
S22-14: Legacy wrapper for il_exec_run.py -> explicitly forbidden.
"""
import sys
from pathlib import Path

def main():
    try:
        print(f"ERROR: legacy entrypoint {Path(__file__).name} is explicitly forbidden. Please use scripts/il_entry.py")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
