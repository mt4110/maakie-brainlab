"""
S22-05: Unified IL Entry Point (Single Entry + Always Verify)

Sequence:
1. Environment Check
2. Validate (Schema + Invariants)
3. Canonicalize (Stable IL)
4. Execute (Opcode processing)
5. Verify (Artifacts check)

STOPLESS: Never uses sys.exit(). Communicates via OK:/ERROR:/SKIP: logs.
"""

import json
import traceback
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure src/ is importable
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Internal imports (relative to repo root)
from src.il_validator import ILValidator, ILCanonicalizer
from src.il_executor import execute_il
from scripts.obs_writer import OBSWriter

def run_il_entry(il_path: str, fixture_db_path: Optional[str] = None):
    obs = OBSWriter("il_entry", repo_root=repo_root)
    obs.log("OK", phase="boot", obs_format="v1", obs_dir=str(obs.obs_dir))
    
    obs.create_dir()

    il_file = Path(il_path)
    if not il_file.exists():
        obs.log("ERROR", phase="boot", reason=f"file_not_found: {il_path}", STOP=1)

    # 2. Validate
    if obs.stop == 0:
        try:
            obs.log("OK", phase="validate", step="start")
            with open(il_file, "r", encoding="utf-8") as f:
                il_data = json.load(f)
            
            validator = ILValidator()
            valid, errors = validator.validate(il_data)
            if not valid:
                obs.log("ERROR", phase="validate", reason=str(errors), STOP=1)
            else:
                obs.log("OK", phase="validate", step="success")
        except Exception as e:
            obs.log("ERROR", phase="validate", reason=str(e), STOP=1)
    else:
        obs.log("SKIP", phase="validate", STOP=1, reason="prior_error")

    # 3. Canonicalize
    canonical_data = None
    if obs.stop == 0:
        try:
            obs.log("OK", phase="canonicalize", step="start")
            canonicalizer = ILCanonicalizer()
            canonical_bytes = canonicalizer.canonicalize(il_data)
            # Write canonical IL for traceability (binary)
            canon_path = obs.obs_dir / "canonical.il.json"
            with open(canon_path, "wb") as f:
                f.write(canonical_bytes)
            # Re-parse for execution as a dict
            canonical_data = json.loads(canonical_bytes)
            obs.log("OK", phase="canonicalize", step="success")
        except Exception as e:
            obs.log("ERROR", phase="canonicalize", reason=str(e), STOP=1)
    else:
        obs.log("SKIP", phase="canonicalize", STOP=1, reason="prior_error")

    # 4. Execute
    report = None
    if obs.stop == 0:
        try:
            obs.log("OK", phase="execute", step="start")
            report = execute_il(canonical_data or il_data, str(obs.obs_dir), fixture_db_path)
            obs.log("OK", phase="execute", step="success", steps=len(report.get("steps", [])))
            obs.write_json("result.json", report)
        except Exception as e:
            obs.log("ERROR", phase="execute", reason=str(e), STOP=1)
            traceback.print_exc()
    else:
        obs.log("SKIP", phase="execute", STOP=1, reason="prior_error")

    # 5. Verify (Artifacts)
    if obs.stop == 0:
        try:
            obs.log("OK", phase="verify", step="start")
            # Simple health check for output
            report_file = obs.obs_dir / "il.exec.report.json"
            if not report_file.exists():
                obs.log("ERROR", phase="verify", reason="artifact_missing", STOP=1)
            else:
                obs.log("OK", phase="verify", step="success")
        except Exception as e:
            obs.log("ERROR", phase="verify", reason=str(e), STOP=1)
    else:
        obs.log("SKIP", phase="verify", STOP=1, reason="prior_error")

    obs.log("OK", phase="end", STOP=obs.stop)
    return obs.stop

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Unified IL Entry Point")
    parser.add_argument("il_path", help="Path to IL JSON file")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--fixture-db", help="Path to fixture DB (optional)")
    
    args = parser.parse_args()
    run_il_entry(args.il_path, args.fixture_db)
