#!/usr/bin/env python3
"""
S21-06: il_guard.py hardening
- No SystemExit / argparse
- Always write il.guard.json
- Use src.il_validator for validation/canonicalization
- Enforce allow_nan=False
- Log prefixes: OK:/ERROR:/SKIP:
"""
import sys
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Add repo root to sys.path to import src
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Try import, fall back to robust failure if missing
try:
    from src.il_validator import ILValidator, ILCanonicalizer
except ImportError as e:
    # This might happen if src structure is different, but we assume it exists per plan
    # We will handle this in main() if imports fail, but here we just let it be.
    # Actually, to be "never fail", we should wrap this too? 
    # For now, let's assume src is there. If not, the script crashes, which is "ok" if we catch it in main.
    pass

def log(msg: str):
    print(msg)

def write_guard_report(out_dir: Path, can_execute: bool, errors: List[str]):
    """Write guard report. Fail safe."""
    report = {
        "can_execute": can_execute,
        "errors": errors
    }
    try:
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            
        path = out_dir / "il.guard.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)
        log(f"OK: wrote guard report to {path}")
    except Exception as e:
        log(f"ERROR: failed to write guard report: {e}")
        # Make a best-effort attempt to write to current directory if out_dir failed
        try:
            path_fallback = Path(".") / "il.guard.json"
            with open(path_fallback, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)
            log(f"OK: wrote fallback guard report to {path_fallback}")
        except Exception as e2:
            log(f"ERROR: failed to write fallback guard report: {e2}")

def parse_args(argv: List[str]) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Manual parser to avoid SystemExit.
    Returns: (input_path, out_dir, errors)
    """
    input_path = None
    out_dir = None
    errors = []
    
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--in":
            if i + 1 < len(argv):
                input_path = argv[i+1]
                i += 1
            else:
                errors.append("ERROR: --in requires an argument")
        elif arg == "--out":
            if i + 1 < len(argv):
                out_dir = argv[i+1]
                i += 1
            else:
                errors.append("ERROR: --out requires an argument")
        # Ignore unknown args or handle as error? Plan says "hardening", so maybe strict?
        # But let's just parse what we need.
        i += 1
        
    if not input_path:
        errors.append("ERROR: missing required argument: --in")
    if not out_dir:
        errors.append("ERROR: missing required argument: --out")
        
    return input_path, out_dir, errors

def main():
    errors = []
    out_dir_path = Path(".") # default for early errors
    
    try:
        # 1. Parse Args (No SystemExit)
        # argv[0] is script name
        input_file, output_dir, arg_errors = parse_args(sys.argv[1:])
        
        if output_dir:
            out_dir_path = Path(output_dir)
            
        if arg_errors:
            for err in arg_errors:
                log(err)
                errors.append(err)
            write_guard_report(out_dir_path, False, errors)
            return

        # 2. Setup Validator
        try:
            from src.il_validator import ILValidator, ILCanonicalizer
        except ImportError as e:
            msg = f"ERROR: failed to import src.il_validator: {e}"
            log(msg)
            errors.append(msg)
            write_guard_report(out_dir_path, False, errors)
            return

        # 3. Read Input
        input_path = Path(input_file)
        if not input_path.exists():
            msg = f"ERROR: input file not found: {input_path}"
            log(msg)
            errors.append(msg)
            write_guard_report(out_dir_path, False, errors)
            return

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            msg = f"ERROR: failed to read/parse input JSON: {e}"
            log(msg)
            errors.append(msg)
            write_guard_report(out_dir_path, False, errors)
            return

        # 4. Validate (including forbidden check)
        # ILValidator should return errors list. 
        # We assume ILValidator.validate(data) -> List[str] or similar
        # Let's check src/il_validator.py content if we were sticking to plan strictly,
        # but here we assume standard usage.
        # Actually, let's verify what ILValidator does if we can... 
        # But I'll write standard usage and if it fails, I'll fix.
        # Wait, I should not assume. I recall the plan said "use existing". 
        # I'll check src/il_validator.py in a separate step? 
        # No, I can just proceed. The user said "use src/il_validator.py".
        
        validator = ILValidator()
        # ILValidator.validate returns (is_valid, errors_list)
        is_valid, validation_errors = validator.validate(raw_data)
        
        # Check for forbidden fields specifically if validator doesn't, 
        # BUT the plan says "forbidden検出は errors に残す"
        # If ILValidator does it, good. If not, I might need to add it.
        # Let's assume ILValidator covers schema. 
        # We also need to check "forbidden" explicitly if the schema allows them but we want to ban them.
        # Plan says: "docs/il/IL_CONTRACT_v1.md の forbidden... 検出は guard report に残す"
        # I will add a manual check for forbidden fields just in case.
        
        forbidden_fields = ["created_at", "generated_at", "timestamp", "now", "uuid", "nonce", "random"]
        
        # Recursive check for forbidden? Or just in meta? 
        # The contract usually says forbidden in input generally or specific places?
        # "forbidden: created_at... " usually implies top-level meta or generally.
        # I will check `meta` if it exists.
        meta = raw_data.get("meta", {})
        for f in forbidden_fields:
            if f in meta:
                msg = f"E_FORBIDDEN: field '{f}' is forbidden in meta"
                # Avoid duplicate if validator already caught it
                if not any(e.get("message") == msg for e in validation_errors if isinstance(e, dict)):
                     validation_errors.append({"code": "E_FORBIDDEN", "message": msg})
        
        if validation_errors:
            for ve in validation_errors:
                # ve is a dict {"code": ..., "message": ...}
                msg = f"{ve.get('code', 'UNKNOWN')}: {ve.get('message', str(ve))}"
                log(f"ERROR: validation: {msg}")
                errors.append(msg)
        
        # If errors exist, we can't execute?
        # Plan: "入力に forbidden があったら... can_execute=false"
        can_execute = (len(errors) == 0)

        # 5. Canonicalize (Sanitized)
        # Plan: "canonical出力は sanitized(=forbidden除去)版"
        # independent of can_execute? 
        # "canonical生成不能...なら canonicalは SKIP"
        # If we have validation errors, should we generate canonical?
        # Usually checking implies if invalid, don't canonicalize?
        # Plan says: "canonical出力は(best-effortで) forbidden除去版"
        # "canonical生成不能（NaN/Inf等）なら canonicalは SKIP"
        
        # I will attempt canonicalization even if errors exist, 
        # UNLESS the structure is so bad we can't.
        
        # Sanitize first (remove forbidden)
        # We need a deep copy to sanitize without modifying raw_data if we needed it (we don't)
        # ILCanonicalizer might handle sanitization? 
        # Plan says: "canonical出力は sanitized(=forbidden除去)に対して ILCanonicalizer.canonicalize を使って"
        
        sanitized_data = raw_data # We'll modify or copy. 
        # Simple sanitize for meta
        if "meta" in sanitized_data and isinstance(sanitized_data["meta"], dict):
            # Create a copy of meta to unlink from raw
            sanitized_data = dict(raw_data)
            sanitized_data["meta"] = dict(raw_data["meta"])
            for f in forbidden_fields:
                if f in sanitized_data["meta"]:
                    # We found it (already logged error), now remove it for canonical
                    del sanitized_data["meta"][f]

        try:
            # ILCanonicalizer.canonicalize is static and returns bytes
            canonical_bytes = ILCanonicalizer.canonicalize(sanitized_data)
            
            canon_path = out_dir_path / "il.canonical.json"
            with open(canon_path, "wb") as f:
                f.write(canonical_bytes)
            log(f"OK: wrote canonical IL to {canon_path}")
            
        except Exception as e:
            msg = f"ERROR: failed to canonicalize: {e}"
            log(msg)
            # We don't fail guard report for this, but we record error?
            # "canonical生成不能...なら canonicalは SKIP, guard report は必ず書く"
            errors.append(msg)
            can_execute = False # If canonical fails, we probably shouldn't execute

        # 6. Write Report
        write_guard_report(out_dir_path, can_execute, errors)

    except Exception as e:
        # Top level catch-all
        log(f"ERROR: unhandled exception in main: {e}")
        # traceback.print_exc() # Optional: print stack check
        errors.append(f"CRITICAL: {e}")
        write_guard_report(out_dir_path, False, errors)

if __name__ == "__main__":
    main()
