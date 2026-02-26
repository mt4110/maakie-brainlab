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

def _resolve_obs_dir(out_dir: Optional[str]) -> Optional[Path]:
    if not out_dir:
        return None
    candidate = Path(out_dir).expanduser()
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def run_il_entry(il_path: str, fixture_db_path: Optional[str] = None, out_dir: Optional[str] = None):
    obs = OBSWriter("il_entry", repo_root=repo_root)
    resolved_out_dir = _resolve_obs_dir(out_dir)
    if resolved_out_dir is not None:
        obs.obs_dir = resolved_out_dir
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
    import sys
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print("OK: usage: python3 scripts/il_entry.py <il_path> --out <out_dir> [--fixture-db <path>]")
    else:
        il_path = None
        out_dir = None
        fixture_db = None
        pos_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--out":
                if i + 1 < len(args):
                    out_dir = args[i+1]
                i += 2
            elif arg == "--fixture-db":
                if i + 1 < len(args):
                    fixture_db = args[i+1]
                i += 2
            else:
                pos_args.append(arg)
                i += 1
        
        if len(pos_args) >= 1:
            il_path = pos_args[0]
            run_il_entry(il_path, fixture_db, out_dir)
        else:
            print("ERROR: missing required argument il_path")
