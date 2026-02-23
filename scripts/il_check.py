#!/usr/bin/env python3
"""
S21-06: il_check.py hardening
- No SystemExit / argparse
- shell=False
- Safe subprocess execution
- Verify generated reports (il.guard.json, il.exec.json)
- Log prefixes: OK:/ERROR:/SKIP:
"""
import sys
import subprocess
import json
import traceback
from pathlib import Path
from typing import List, Tuple, Any

def log(msg: str):
    print(msg)

def run_safe(cmd: List[str]) -> Tuple[int, str, str]:
    """
    Run command safely with shell=False.
    Returns (rc, stdout, stderr).
    Does NOT exit on failure.
    """
    try:
        # capture_output=True -> stdout/stderr are bytes
        # text=True -> decode to string
        p = subprocess.run(cmd, shell=False, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        log(f"ERROR: subprocess failed: {e}")
        return -1, "", str(e)

def check_fixture(name: str, in_path: Path, expect_can_exec: bool) -> bool:
    """
    Run guard -> exec cycle for a fixture.
    Returns True if passed (expectations met), False otherwise.
    """
    out_dir = Path(f".local/check_{name}")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log(f"ERROR: [{name}] failed to create out_dir: {e}")
        return False
    
    script_guard = Path("scripts/il_guard.py")
    script_exec = Path("scripts/il_exec.py")
    
    if not script_guard.exists() or not script_exec.exists():
        log(f"ERROR: [{name}] missing scripts")
        return False

    # 1. Guard
    # cmd: python scripts/il_guard.py --in ... --out ...
    cmd_guard = [sys.executable, str(script_guard), "--in", str(in_path), "--out", str(out_dir)]
    rc, out, err = run_safe(cmd_guard)
    
    # We check expected file existence, not just RC (though RC should be 0 unless crash)
    # il_guard is designed to write report even on failure.
    
    guard_json = out_dir / "il.guard.json"
    if not guard_json.exists():
        log(f"ERROR: [{name}] guard produced no json (rc={rc})")
        if out: log(f"STDOUT: {out}")
        if err: log(f"STDERR: {err}")
        return False
    
    try:
        with open(guard_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        can_exec = data.get("can_execute")
        errors = data.get("errors", [])
        
        if can_exec != expect_can_exec:
            log(f"ERROR: [{name}] expect can_execute={expect_can_exec}, got {can_exec}")
            log(f"       Errors: {errors}")
            return False
            
    except Exception as e:
        log(f"ERROR: [{name}] failed to parse guard json: {e}")
        return False

    # 2. Exec
    # Exec depends on canonical output from guard
    # If guard failed (expect_can_exec=False), canonical might not exist or be invalid, 
    # BUT we should still run exec to verify it handles it (SKIP).
    
    canon_path = out_dir / "il.canonical.json"
    
    # If we expected success but canonical doesn't exist -> fail
    if expect_can_exec and not canon_path.exists():
        log(f"ERROR: [{name}] expect success but canonical missing")
        return False
        
    # If we expected failure, canonical *might* exist if validation failed but canonicalization worked?
    # Our guard logic: canonicalizes first? No, read -> canonicalize -> validate.
    # If validation fails, canonical file exists.
    # If read fails, no canonical.
    # So canonical path likely exists unless read failed.
    # We pass it to exec anyway. Exec should be robust.
    
    # cmd: python scripts/il_exec.py --il ... --guard ... --out ...
    cmd_exec = [sys.executable, str(script_exec), "--il", str(canon_path), "--guard", str(guard_json), "--out", str(out_dir)]
    rc, out, err = run_safe(cmd_exec)
    
    exec_json = out_dir / "il.exec.json"
    if not exec_json.exists():
        log(f"ERROR: [{name}] exec produced no json (rc={rc})")
        if out: log(f"STDOUT: {out}")
        if err: log(f"STDERR: {err}")
        return False
        
    try:
        with open(exec_json, "r", encoding="utf-8") as f:
            edata = json.load(f)
        status = edata.get("status")
        
        if expect_can_exec:
            if status != "OK":
                log(f"ERROR: [{name}] expect exec STATUS=OK, got {status}")
                return False
        else:
            if status != "SKIP":
                log(f"ERROR: [{name}] expect exec STATUS=SKIP, got {status}")
                return False
                
    except Exception as e:
        log(f"ERROR: [{name}] failed to parse exec json: {e}")
        return False
        
    log(f"OK: [{name}] passed")
    return True

def main():
    log("SKIP: legacy entrypoint il_check.py is deprecated. Use scripts/il_entry.py")
    try:
        log("=== IL Verification Checks (Hardened) ===")
        
        # Fixtures
        fixtures_dir = Path("tests/fixtures/il")
        good = fixtures_dir / "good" / "minimal.json"
        
        # We need a 'bad' fixture to test rejection. 
        # Does tests/fixtures/il/bad exist?
        bad_dir = fixtures_dir / "bad"
        bad = None
        if bad_dir.exists():
            # Find any json in bad
            bad_files = list(bad_dir.glob("*.json"))
            if bad_files:
                bad = bad_files[0]
        
        failed = 0
        total = 0
        
        # Test Good
        if good.exists():
            total += 1
            if not check_fixture("good_minimal", good, True):
                failed += 1
        else:
            log(f"SKIP: good fixture not found at {good}")
            
        # Test Bad (if exists)
        if bad and bad.exists():
            total += 1
            if not check_fixture("bad_example", bad, False):
                failed += 1
        else:
            # Create a temporary bad fixture if none?
            # Or just skip. Plan says "scripts/il_check.py" verification. 
            # I'll rely on existing.
            log("SKIP: no bad fixture found to test rejection")

        if failed > 0:
            log(f"ERROR: {failed}/{total} checks failed")
            # Exit 0 always per policy
        else:
            log(f"OK: all {total} checks passed")
            
    except Exception as e:
        log(f"ERROR: unhandled exception in check main: {e}")
        # traceback.print_exc()

if __name__ == "__main__":
    main()
