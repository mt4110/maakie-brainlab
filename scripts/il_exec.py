#!/usr/bin/env python3
import argparse
import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

def log(msg: str):
    print(msg)

def write_exec_report(out_dir: Path, status: str, details: List[str]):
    report = {
        "status": status,
        "details": details
    }
    path = out_dir / "il.exec.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        log(f"OK: wrote exec report to {path}")
    except Exception as e:
        log(f"ERROR: failed to write exec report: {e}")

def opcode_noop(args: Any, ctx: Dict) -> str:
    return "OK: NOOP"

def opcode_set_vars(args: Any, ctx: Dict) -> str:
    # args: {"key": "val", ...}
    if isinstance(args, dict):
        for k, v in args.items():
            ctx["vars"][k] = v
        return f"OK: SET_VARS {len(args)} vars"
    return "ERROR: SET_VARS args must be dict"

def opcode_search_terms(args: Any, ctx: Dict) -> str:
    # args: ["term1", "term2"]
    if isinstance(args, list):
        # We don't actually search in this minimal executor, just log
        return f"OK: SEARCH_TERMS {args}"
    return "ERROR: SEARCH_TERMS args must be list"

def opcode_retrieve(args: Any, ctx: Dict) -> str:
    # args: {"query": "..."}
    # Minimal implementation: always SKIP or EMPTY
    return "SKIP: RETRIEVE not connected"

def opcode_answer_draft(args: Any, ctx: Dict) -> str:
    # args: {"template": "..."}
    # Minimal: just log
    return "OK: ANSWER_DRAFT prepared"

OPCODES = {
    "NOOP": opcode_noop,
    "SET_VARS": opcode_set_vars,
    "SEARCH_TERMS": opcode_search_terms,
    "RETRIEVE": opcode_retrieve,
    "ANSWER_DRAFT": opcode_answer_draft,
}

def main():
    parser = argparse.ArgumentParser(description="IL Executor: Minimal & Deterministic")
    parser.add_argument("--il", dest="il_path", required=True, help="Path to canonical IL")
    parser.add_argument("--guard", dest="guard_path", required=True, help="Path to guard JSON")
    parser.add_argument("--out", dest="out_dir", required=True, help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    details = []

    # 1. Check Guard
    try:
        with open(args.guard_path, "r", encoding="utf-8") as f:
            guard = json.load(f)
        
        if not guard.get("can_execute"):
            msg = "SKIP: guard blocks execution"
            log(msg)
            write_exec_report(out_dir, "SKIP", [msg])
            return

    except Exception as e:
        msg = f"ERROR: failed to read guard: {e}"
        log(msg)
        write_exec_report(out_dir, "ERROR", [msg])
        return

    # 2. Read IL
    try:
        with open(args.il_path, "r", encoding="utf-8") as f:
            il_data = json.load(f)
        
        # We assume IL structure: {"il": { "opcodes": [...] }, ...}
        # But schema says "il": { "type": "object" }, so we need to define internal structure for opcodes.
        # For now, let's assume `il.opcodes` list of `{"op": "NAME", "args": ...}`
        
        il_body = il_data.get("il", {})
        opcodes = il_body.get("opcodes", [])
        
        ctx = {"vars": {}}
        
        for i, op_def in enumerate(opcodes):
            op_name = op_def.get("op")
            op_args = op_def.get("args")
            
            handler = OPCODES.get(op_name)
            if handler:
                res = handler(op_args, ctx)
                log(f"[{i}] {op_name}: {res}")
                details.append(f"[{i}] {op_name}: {res}")
            else:
                msg = f"SKIP: unknown opcode {op_name}"
                log(f"[{i}] {msg}")
                details.append(f"[{i}] {msg}")
        
    except Exception as e:
        msg = f"ERROR: execution failed: {e}"
        log(msg)
        details.append(msg)
        write_exec_report(out_dir, "ERROR", details)
        return

    write_exec_report(out_dir, "OK", details)
    log("OK: execution finished")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: unhandled exception in executor: {e}")
