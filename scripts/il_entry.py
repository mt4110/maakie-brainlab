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

def log(level: str, msg: str):
    """Unified log printer."""
    print(f"{level}: {msg}")

def run_il_entry(il_path: str, out_dir: str, fixture_db_path: Optional[str] = None):
    STOP = 0
    # repo_root already defined above
    
    # 1. Environment Check
    log("OK", f"entry run starting il_path={il_path} out_dir={out_dir}")
    
    il_file = Path(il_path)
    if not il_file.exists():
        log("ERROR", f"IL file not found: {il_path}")
        STOP = 1
    
    out_path = Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log("ERROR", f"Failed to create out_dir={out_dir} err={e}")
        STOP = 1

    # 2. Validate
    if STOP == 0:
        try:
            log("OK", "starting step=VALIDATE")
            with open(il_file, "r", encoding="utf-8") as f:
                il_data = json.load(f)
            
            validator = ILValidator()
            valid, errors = validator.validate(il_data)
            if not valid:
                log("ERROR", f"IL validation failed: {errors}")
                STOP = 1
            else:
                log("OK", "step succeeded step=VALIDATE")
        except Exception as e:
            log("ERROR", f"Validation exception: {e}")
            STOP = 1
    else:
        log("SKIP", "step=VALIDATE blocked by previous ERROR")

    # 3. Canonicalize
    canonical_data = None
    if STOP == 0:
        try:
            log("OK", "starting step=CANONICALIZE")
            canonicalizer = ILCanonicalizer()
            canonical_bytes = canonicalizer.canonicalize(il_data)
            # Write canonical IL for traceability (binary)
            canon_path = out_path / "canonical.il.json"
            with open(canon_path, "wb") as f:
                f.write(canonical_bytes)
            # Re-parse for execution as a dict
            canonical_data = json.loads(canonical_bytes)
            log("OK", "step succeeded step=CANONICALIZE")
        except Exception as e:
            log("ERROR", f"Canonicalization exception: {e}")
            STOP = 1
    else:
        log("SKIP", "step=CANONICALIZE blocked by previous ERROR")

    # 4. Execute
    report = None
    if STOP == 0:
        try:
            log("OK", "starting step=EXECUTE")
            report = execute_il(canonical_data or il_data, str(out_path), fixture_db_path)
            log("OK", f"step succeeded step=EXECUTE steps={len(report.get('steps', []))}")
        except Exception as e:
            log("ERROR", f"Execution exception: {e}")
            traceback.print_exc()
            STOP = 1
    else:
        log("SKIP", "step=EXECUTE blocked by previous ERROR")

    # 5. Verify (Artifacts)
    if STOP == 0:
        try:
            log("OK", "starting step=VERIFY")
            # Simple health check for output
            report_file = out_path / "il.exec.report.json"
            if not report_file.exists():
                log("ERROR", "Artifact missing: report.json")
                STOP = 1
            else:
                log("OK", "step succeeded step=VERIFY")
        except Exception as e:
            log("ERROR", f"Verification exception: {e}")
            STOP = 1
    else:
        log("SKIP", "step=VERIFY blocked by previous ERROR")

    log("OK", f"pipeline finished STOP={STOP}")
    return STOP

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Unified IL Entry Point")
    parser.add_argument("il_path", help="Path to IL JSON file")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--fixture-db", help="Path to fixture DB (optional)")
    
    args = parser.parse_args()
    run_il_entry(args.il_path, args.out, args.fixture_db)
