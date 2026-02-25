#!/usr/bin/env python3
"""
S22-14: Legacy wrapper for il_exec.py -> explicitly forbidden.
"""
import sys

def main():
    try:
        print(f"ERROR: legacy entrypoint {sys.argv[0]} is explicitly forbidden. Please use scripts/il_entry.py")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
