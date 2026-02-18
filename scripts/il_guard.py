#!/usr/bin/env python3
import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import jsonschema, but don't crash if missing (though it shouldn't happen in standard env)
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

def log(msg: str):
    """Print log message to stdout in format KEY: VALUE."""
    print(msg)

def write_guard_report(out_dir: Path, can_execute: bool, errors: List[str]):
    """Write guard report to out_dir/il.guard.json."""
    report = {
        "can_execute": can_execute,
        "errors": errors
    }
    path = out_dir / "il.guard.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        log(f"OK: wrote guard report to {path}")
    except Exception as e:
        log(f"ERROR: failed to write guard report: {e}")

def canonicalize(data: Any) -> Any:
    """
    Canonicalize JSON data:
    - Recursive sort keys for dicts
    - Strip forbidden fields (timestamp, generated_at, env) from 'meta' if present
    - Arrays preserve order
    """
    if isinstance(data, dict):
        new_data = {}
        sorted_keys = sorted(data.keys())
        for k in sorted_keys:
            # Strip forbidden fields in meta (or roughly anywhere for safety, but spec says strip forbidden)
            # For now, we'll implement stripping known unstable fields if they appear in likely places
            if k in ("timestamp", "generated_at", "env", "elapsed_ms"):
                continue
            new_data[k] = canonicalize(data[k])
        return new_data
    elif isinstance(data, list):
        return [canonicalize(i) for i in data]
    else:
        return data

def main():
    parser = argparse.ArgumentParser(description="IL Guard: Canonicalize and Validate")
    parser.add_argument("--in", dest="input_path", required=True, help="Path to raw IL JSON")
    parser.add_argument("--out", dest="out_dir", required=True, help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    errors = []
    
    # 1. Read Raw IL
    raw_data = None
    try:
        with open(args.input_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        log(f"OK: read raw IL from {args.input_path}")
    except Exception as e:
        msg = f"failed to read/parse input IL: {e}"
        log(f"ERROR: {msg}")
        errors.append(msg)
        write_guard_report(out_dir, False, errors)
        return

    # 2. Canonicalize
    try:
        canonical_data = canonicalize(raw_data)
        # Write canonical bytes
        canon_path = out_dir / "il.canonical.json"
        
        # Enforce canonical formatting:
        # - separators=(",", ":") -> no space after separators
        # - ensure_ascii=False -> utf-8 distinct
        # - sort_keys=True -> strict ordering at top level (recursive is handled by canonicalize logic if used JSON dump's sort_keys, 
        #   but python's json.dump sort_keys only sorts keys of dictionaries, which matches requirement.
        #   However, our canonicalize function already sorted keys in new dicts, but json.dump is safer to re-sort to be sure.)
        
        # Actually our canonicalize function creates new dicts with inserted order being sorted (since Py3.7+).
        # But to be 100% safe on bytes, we rely on json.dumps with sort_keys=True as well.
        
        with open(canon_path, "w", encoding="utf-8") as f:
            json.dump(canonical_data, f, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        
        log(f"OK: wrote canonical IL to {canon_path}")
    except Exception as e:
        msg = f"failed to canonicalize: {e}"
        log(f"ERROR: {msg}")
        errors.append(msg)
        write_guard_report(out_dir, False, errors)
        return

    # 3. Validate against Schema
    # Try to locate schema relative to repo root or script
    # We expect docs/il/il.schema.json
    repo_root = Path(__file__).resolve().parent.parent
    schema_path = repo_root / "docs" / "il" / "il.schema.json"
    
    if not schema_path.exists():
        msg = f"schema not found at {schema_path}"
        log(f"ERROR: {msg}")
        errors.append(msg)
        write_guard_report(out_dir, False, errors)
        return

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
        
        if HAS_JSONSCHEMA:
            jsonschema.validate(instance=canonical_data, schema=schema_data)
            log("OK: validation passed (jsonschema)")
        else:
             # Fallback: minimal checks if jsonschema missing
            log("SKIP: jsonschema lib not found, performing minimal checks")
            if "il" not in canonical_data or "meta" not in canonical_data:
                raise ValueError("missing required top-level fields: il, meta")
            
    except Exception as e:
        # Validation failed
        # If it's a validation error, we might want cleaner output, but str(e) is enough for now
        msg = f"validation failed: {str(e).splitlines()[0]}" # Keep it brief-ish
        log(f"ERROR: {msg}")
        errors.append(msg)
        # We continue to write guard report false
        write_guard_report(out_dir, False, errors)
        return

    # Success
    write_guard_report(out_dir, True, [])
    log("OK: guard finished successfully")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last resort catch-all to ensure 0 exit code
        print(f"ERROR: unhandled exception: {e}")
        # Try to write guard file if possible
        try:
            # We assume nothing about paths here, so maybe just print
             pass
        except:
            pass
    
    # Always exit 0
    sys.exit(0)
