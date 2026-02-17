#!/usr/bin/env python3
"""
py_env_report.py
Reports the current Python environment status (executable, venv, prefixes)
in a safe, non-crashing manner.
"""
import sys
import os
import json

def safe_print(label, value):
    try:
        print(f"{label}: {value}")
    except Exception:
        pass

def main():
    try:
        print("=== Python Environment Report ===")
        safe_print("sys.executable", sys.executable)
        safe_print("sys.prefix", sys.prefix)
        safe_print("sys.base_prefix", getattr(sys, "base_prefix", "N/A"))
        
        # Check if in venv
        is_venv = (sys.prefix != getattr(sys, "base_prefix", sys.prefix))
        safe_print("is_venv", is_venv)
        
        # Check pip usage env vars
        pip_config = os.environ.get("PIP_CONFIG_FILE", "N/A")
        safe_print("PIP_CONFIG_FILE", pip_config)
        
        # Check specific prohibited vars (like PIP_USER)
        # Note: PIP_USER might be set in config, harder to check without pip debug
        # But we can check env
        pip_user_env = os.environ.get("PIP_USER", "N/A")
        safe_print("PIP_USER (env)", pip_user_env)

        # Check CWD
        safe_print("CWD", os.getcwd())

        # Simple verification of expected path
        # We expect to be running under .venv/bin/python usually
        if ".venv" in sys.executable:
            print("OK: Running inside .venv")
        else:
            print("WARN: Not running inside .venv (or path doesn't contain '.venv')")

    except Exception as e:
        # Fallback for ANY error
        print(f"ERROR: py_env_report.py failed: {e}")

if __name__ == "__main__":
    main()
