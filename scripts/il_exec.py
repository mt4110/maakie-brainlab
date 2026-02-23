#!/usr/bin/env python3
"""
S21-06: il_exec.py hardening
- No SystemExit / argparse
- Always write il.exec.json
- Status aggregation (ERROR > OK > SKIP)
- Log prefixes: OK:/ERROR:/SKIP:
"""
import sys
import json
import math
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def log(msg: str):
    print(msg)

def clean_for_json(obj: Any) -> Any:
    """
    Recursively replace NaN/Infinity with None for strict JSON compliance.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    return obj

def write_exec_report(out_dir: Path, status: str, details: List[str]):
    """Write exec report. Fail safe."""
    report = {
        "status": status,
        "details": details
    }
    try:
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            
        path = out_dir / "il.exec.json"
        
        # S21-07: Hardening JSON output
        report_clean = clean_for_json(report)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_clean, f, indent=2, ensure_ascii=False, allow_nan=False)
        log(f"OK: wrote exec report to {path} (status={status})")
    except Exception as e:
        log(f"ERROR: failed to write exec report: {e}")
        # best-effort fallback
        try:
            path_fallback = Path(".") / "il.exec.json"
            
            # S21-07: Hardening JSON output (fallback)
            report_clean = clean_for_json(report)
            
            with open(path_fallback, "w", encoding="utf-8") as f:
                json.dump(report_clean, f, indent=2, ensure_ascii=False, allow_nan=False)
            log(f"OK: wrote fallback exec report to {path_fallback}")
        except Exception as e2:
            log(f"ERROR: failed to write fallback exec report: {e2}")

def parse_args(argv: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
    """
    Manual parser.
    Returns: (il_path, guard_path, out_dir, errors)
    """
    il_path = None
    guard_path = None
    out_dir = None
    errors = []
    
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--il":
            if i + 1 < len(argv):
                il_path = argv[i+1]
                i += 1
            else:
                errors.append("ERROR: --il requires an argument")
        elif arg == "--guard":
            if i + 1 < len(argv):
                guard_path = argv[i+1]
                i += 1
            else:
                errors.append("ERROR: --guard requires an argument")
        elif arg == "--out":
            if i + 1 < len(argv):
                out_dir = argv[i+1]
                i += 1
            else:
                errors.append("ERROR: --out requires an argument")
        i += 1
        
    if not il_path:
        errors.append("ERROR: missing required argument: --il")
    if not guard_path:
        errors.append("ERROR: missing required argument: --guard")
    if not out_dir:
        errors.append("ERROR: missing required argument: --out")
        
    return il_path, guard_path, out_dir, errors

# --- Opcode Handlers ---

def opcode_noop(args: Any, ctx: Dict) -> str:
    return "OK: NOOP"

def opcode_set_vars(args: Any, ctx: Dict) -> str:
    if isinstance(args, dict):
        for k, v in args.items():
            ctx["vars"][k] = v
        return f"OK: SET_VARS {len(args)} vars"
    return "ERROR: SET_VARS args must be dict"

def opcode_search_terms(args: Any, ctx: Dict) -> str:
    if isinstance(args, list):
        return f"OK: SEARCH_TERMS {args}"
    return "ERROR: SEARCH_TERMS args must be list"

def opcode_retrieve(args: Any, ctx: Dict) -> str:
    return "SKIP: RETRIEVE not connected"

def opcode_answer_draft(args: Any, ctx: Dict) -> str:
    return "OK: ANSWER_DRAFT prepared"

OPCODES = {
    "NOOP": opcode_noop,
    "SET_VARS": opcode_set_vars,
    "SEARCH_TERMS": opcode_search_terms,
    "RETRIEVE": opcode_retrieve,
    "ANSWER_DRAFT": opcode_answer_draft,
}

def determine_status(results: List[str]) -> str:
    """
    Aggregate status:
    - If ANY result starts with ERROR: -> ERROR
    - Else if ANY result starts with OK: -> OK
    - Else -> SKIP (or empty)
    """
    has_ok = False
    for res in results:
        if res.startswith("ERROR:"):
            return "ERROR"
        if res.startswith("OK:"):
            has_ok = True
    
    if has_ok:
        return "OK"
    return "SKIP"

def main():
    details = []
    out_dir_path = Path(".")
    
    log("SKIP: legacy entrypoint il_exec.py is deprecated. Use scripts/il_entry.py")
    
    try:
        # 1. Parse Args
        il_file, guard_file, out_dir, arg_errors = parse_args(sys.argv[1:])
        
        if out_dir:
            out_dir_path = Path(out_dir)
            
        if arg_errors:
            for err in arg_errors:
                log(err)
                details.append(err)
            write_exec_report(out_dir_path, "ERROR", details)
            return

        # 2. Check Guard
        guard_path = Path(guard_file)
        if not guard_path.exists():
            msg = f"ERROR: guard file not found: {guard_path}"
            log(msg)
            details.append(msg)
            write_exec_report(out_dir_path, "ERROR", details)
            return
            
        try:
            with open(guard_path, "r", encoding="utf-8") as f:
                guard_data = json.load(f)
            
            if not guard_data.get("can_execute"):
                msg = "SKIP: guard blocks execution (can_execute=false)"
                log(msg)
                details.append(msg)
                write_exec_report(out_dir_path, "SKIP", details)
                return
                
        except Exception as e:
            msg = f"ERROR: failed to read guard: {e}"
            log(msg)
            details.append(msg)
            write_exec_report(out_dir_path, "ERROR", details)
            return

        # 3. Read IL
        il_path = Path(il_file)
        if not il_path.exists():
            msg = f"ERROR: IL file not found: {il_path}"
            log(msg)
            details.append(msg)
            write_exec_report(out_dir_path, "ERROR", details)
            return
            
        try:
            with open(il_path, "r", encoding="utf-8") as f:
                il_data = json.load(f)
        except Exception as e:
            msg = f"ERROR: failed to read IL: {e}"
            log(msg)
            details.append(msg)
            write_exec_report(out_dir_path, "ERROR", details)
            return
            
        # 4. Execute Opcodes
        il_body = il_data.get("il", {})
        opcodes = il_body.get("opcodes", [])
        
        ctx = {"vars": {}}
        results = []
        
        for i, op_def in enumerate(opcodes):
            op_name = op_def.get("op")
            op_args = op_def.get("args")
            
            handler = OPCODES.get(op_name)
            
            # S21-07: Log formatting
            status_prefix = "SKIP"
            message = ""
            
            if handler:
                try:
                    res_raw = handler(op_args, ctx)
                    # Handlers return "STATUS: message"
                    if res_raw.startswith("OK:"):
                        status_prefix = "OK"
                        message = res_raw[3:].strip()
                    elif res_raw.startswith("ERROR:"):
                        status_prefix = "ERROR"
                        message = res_raw[6:].strip()
                    elif res_raw.startswith("SKIP:"):
                        status_prefix = "SKIP"
                        message = res_raw[5:].strip()
                    else:
                        # Fallback if handler breaks contract
                        status_prefix = "OK"
                        message = res_raw
                except Exception as e:
                    status_prefix = "ERROR"
                    message = f"exception in handler {op_name}: {e}"
            else:
                status_prefix = "SKIP"
                message = f"unknown opcode {op_name}"
            
            # Format: STATUS: [i=N] OP: Message
            log_line = f"{status_prefix}: [i={i}] {op_name}: {message}"
            log(log_line)
            
            # Keep log lines as results/details
            results.append(log_line)
            details.append(log_line)
            
        # 5. Aggregate Status
        final_status = determine_status(results)
        write_exec_report(out_dir_path, final_status, details)
        
    except Exception as e:
        log(f"ERROR: unhandled exception in executor: {e}")
        details.append(f"CRITICAL: {e}")
        write_exec_report(out_dir_path, "ERROR", details)

if __name__ == "__main__":
    main()
