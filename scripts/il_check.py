#!/usr/bin/env python3
import sys
import subprocess
import json
from pathlib import Path

def log(msg):
    print(msg)

def run(cmd):
    """Run command, return (rc, stdout, stderr). We don't exit on fail here."""
    log(f"RUN: {cmd}")
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def check_fixture(name, in_path, expect_can_exec):
    out_dir = Path(f".local/check_{name}")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Guard
    rc, _, _ = run(f"python3 scripts/il_guard.py --in {in_path} --out {out_dir}")
    if rc != 0:
        log(f"ERROR: [{name}] guard crashed rc={rc}")
        return False
    
    guard_json = out_dir / "il.guard.json"
    if not guard_json.exists():
        log(f"ERROR: [{name}] guard produced no json")
        return False
    
    try:
        with open(guard_json) as f:
            data = json.load(f)
        can_exec = data.get("can_execute")
        if can_exec != expect_can_exec:
            log(f"ERROR: [{name}] expect can_execute={expect_can_exec}, got {can_exec}")
            return False
    except Exception as e:
        log(f"ERROR: [{name}] failed to parse guard json: {e}")
        return False

    # 2. Exec
    canon_path = out_dir / "il.canonical.json" # Guard should produce this even on failure?
    # Guard logic: "write artifacts always (even if can_execute=false)" -> Yes, except if input read fails completely.
    # But for "bad" fixture (invalid schema), it should exist.
    
    rc, _, _ = run(f"python3 scripts/il_exec.py --il {canon_path} --guard {guard_json} --out {out_dir}")
    if rc != 0:
        log(f"ERROR: [{name}] exec crashed rc={rc}")
        return False
    
    exec_json = out_dir / "il.exec.json"
    if not exec_json.exists():
        log(f"ERROR: [{name}] exec produced no json")
        return False
        
    try:
        with open(exec_json) as f:
            edata = json.load(f)
        status = edata.get("status")
        if expect_can_exec and status != "OK":
            log(f"ERROR: [{name}] expect exec STATUS=OK, got {status}")
            return False
        if not expect_can_exec and status != "SKIP":
            log(f"ERROR: [{name}] expect exec STATUS=SKIP, got {status}")
            return False
    except Exception as e:
        log(f"ERROR: [{name}] failed to parse exec json: {e}")
        return False
        
    log(f"OK: [{name}] passed")
    return True

def main():
    log("=== IL Verification Checks ===")
    
    # Fixtures
    fixtures_dir = Path("tests/fixtures/il")
    good = fixtures_dir / "good" / "minimal.json"
    bad = fixtures_dir / "bad" / "invalid.json"
    
    failed = 0
    
    if not check_fixture("good_minimal", good, True):
        failed += 1
        
    if not check_fixture("bad_invalid", bad, False):
        failed += 1
        
    if failed > 0:
        log(f"ERROR: {failed} checks failed")
        # We purposely exit 0 but log ERROR as per "No-exit philosophy" 
        # BUT for a check script that runs in CI, we probably want to fail the CI job 
        # OR we want CI to grep for ERROR.
        # The user said: "CIは “scriptの終了コード” ではなくログ/出力ファイルを成果物として残す... 実行の真偽は... il.guard.json... が真実"
        # However, for a check script itself, usually we want some signal. 
        # But looking at "S21-05 TASK": "ただし ERROR: 行が出る＝失敗の真実（CI/merge guardが拾える）"
        # So exit 0 is correct.
    else:
        log("OK: all checks passed")

if __name__ == "__main__":
    main()
