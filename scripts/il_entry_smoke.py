"""
S22-05: Smoke Test Runner for IL Entry

Test cases:
1. Valid IL (il_min.json) -> Should produce OK for all steps.
2. Invalid IL (Schema violation) -> Should produce ERROR at VALIDATE and SKIP later.
"""

import os
import subprocess
from pathlib import Path

def log(lvl: str, msg: str):
    print(f"{lvl}: {msg}")

def run_smoke():
    repo_root = Path(__file__).resolve().parent.parent
    scripts_dir = repo_root / "scripts"
    il_entry = scripts_dir / "il_entry.py"
    fixtures_dir = repo_root / "tests" / "fixtures" / "il_exec"
    out_base = repo_root / ".local" / "obs" / "il_entry_smoke"
    
    os.makedirs(out_base, exist_ok=True)
    
    cases = [
        {
            "name": "good_minimal",
            "il": fixtures_dir / "il_min.json",
            "db": fixtures_dir / "retrieve_db.json",
            "expect_stop": 0
        },
        {
            "name": "bad_schema",
            "il": None, # Will create a temporary bad file
            "db": None,
            "expect_stop": 1
        }
    ]
    
    results = {"OK": 0, "ERROR": 0, "SKIP": 0}
    
    for case in cases:
        name = case["name"]
        log("OK", f"Starting smoke case={name}")
        
        il_path = case["il"]
        if name == "bad_schema":
            il_path = out_base / "bad_schema.json"
            with open(il_path, "w") as f:
                f.write('{"invalid": "format", "missing": "version"}')
        
        out_dir = out_base / name
        os.makedirs(out_dir, exist_ok=True)
        
        cmd = ["python3", str(il_entry), str(il_path), "--out", str(out_dir)]
        if case["db"]:
            cmd += ["--fixture-db", str(case["db"])]
            
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root)
        
        try:
            # || true pattern: always return 0, capture output
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
            output = proc.stdout + proc.stderr
            print(output)
            
            # Count tags in output
            for line in output.splitlines():
                if line.startswith("OK:"): results["OK"] += 1
                if line.startswith("ERROR:"): results["ERROR"] += 1
                if line.startswith("SKIP:"): results["SKIP"] += 1
            
            # Verification logic for the smoke test results
            if case["expect_stop"] == 0:
                if "pipeline finished STOP=0" in output:
                    log("OK", f"Case {name} passed as expected.")
                else:
                    log("ERROR", f"Case {name} failed: expected STOP=0 but got non-zero.")
            else:
                if "pipeline finished STOP=1" in output:
                    log("OK", f"Case {name} failed (STOP=1) as expected.")
                else:
                    log("ERROR", f"Case {name} passed: expected STOP=1 but got STOP=0.")
                    
        except Exception as e:
            log("ERROR", f"Smoke runner exception case={name} err={e}")
            
    log("OK", f"Smoke summary: OK={results['OK']} ERROR={results['ERROR']} SKIP={results['SKIP']}")

if __name__ == "__main__":
    run_smoke()
