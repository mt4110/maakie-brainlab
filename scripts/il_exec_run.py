#!/usr/bin/env python3
"""
S22-02: IL executor CLI (P2 minimal)
- No sys.exit / SystemExit / assert
- Always writes il.exec.report.json (even on unhandled exception)
- Writes il.exec.result.json only when overall_status == "OK"
- Log prefixes: OK:/ERROR:/SKIP:
"""
import sys
import json
from pathlib import Path
from typing import List, Optional, Tuple


def log(msg: str):
    print(msg)


def parse_args(argv: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
    """
    Manual parser (no argparse -> no SystemExit).
    Returns: (il_path, fixture_db_path, out_dir, errors)
    """
    il_path = None
    fixture_db_path = None
    out_dir = None
    errors: List[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--in":
            if i + 1 < len(argv):
                il_path = argv[i + 1]
                i += 1
            else:
                errors.append("--in requires an argument")
        elif arg == "--fixture-db":
            if i + 1 < len(argv):
                fixture_db_path = argv[i + 1]
                i += 1
            else:
                errors.append("--fixture-db requires an argument")
        elif arg == "--out-dir":
            if i + 1 < len(argv):
                out_dir = argv[i + 1]
                i += 1
            else:
                errors.append("--out-dir requires an argument")
        i += 1

    if not il_path:
        errors.append("missing required argument: --in")
    if not out_dir:
        out_dir = ".local/out"

    return il_path, fixture_db_path, out_dir, errors


def main():
    out_dir = ".local/out"
    try:
        # Import executor from src
        try:
            from il_executor import execute_il, write_json
        except ImportError:
            # Try relative import path
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
            from il_executor import execute_il, write_json

        # Parse args
        il_path, fixture_db_path, out_dir_parsed, arg_errors = parse_args(sys.argv[1:])
        if out_dir_parsed:
            out_dir = out_dir_parsed

        if arg_errors:
            # Write error report and return
            error_report = {
                "schema": "IL_EXEC_REPORT_v1",
                "overall_status": "ERROR",
                "steps": [],
            }
            for err in arg_errors:
                error_report["steps"].append({
                    "index": 0,
                    "opcode": "CLI_ARGS",
                    "status": "ERROR",
                    "reason": err,
                    "in_summary": "CLI arguments",
                    "out_summary": {},
                })
                log(f"ERROR: {err}")

            try:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                write_json(str(Path(out_dir) / "il.exec.report.json"), error_report)
                log(f"OK: wrote {out_dir}/il.exec.report.json (status=ERROR)")
            except Exception as we:
                log(f"ERROR: failed to write report: {we}")
            return

        # Read IL
        try:
            with open(il_path, "r", encoding="utf-8") as f:
                il_data = json.load(f)
        except Exception as e:
            error_report = {
                "schema": "IL_EXEC_REPORT_v1",
                "overall_status": "ERROR",
                "steps": [{
                    "index": 0,
                    "opcode": "READ_IL",
                    "status": "ERROR",
                    "reason": f"failed to read IL: {type(e).__name__}: {e}",
                    "in_summary": f"path: {il_path}",
                    "out_summary": {},
                }],
            }
            try:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                write_json(str(Path(out_dir) / "il.exec.report.json"), error_report)
                log(f"ERROR: failed to read IL: {e}")
                log(f"OK: wrote {out_dir}/il.exec.report.json (status=ERROR)")
            except Exception as we:
                log(f"ERROR: failed to write report: {we}")
            return

        # Execute
        report = execute_il(il_data, out_dir, fixture_db_path)
        overall = report.get("overall_status", "ERROR")

        log(f"{overall}: executor finished (overall_status={overall})")
        log(f"OK: wrote {out_dir}/il.exec.report.json")
        if overall == "OK":
            log(f"OK: wrote {out_dir}/il.exec.result.json")

    except Exception as e:
        # Top-level catch: write emergency report
        log(f"ERROR: unhandled exception: {type(e).__name__}: {e}")
        emergency_report = {
            "schema": "IL_EXEC_REPORT_v1",
            "overall_status": "ERROR",
            "steps": [{
                "index": 0,
                "opcode": "UNHANDLED",
                "status": "ERROR",
                "reason": f"unhandled exception: {type(e).__name__}: {e}",
                "in_summary": "top-level catch",
                "out_summary": {},
            }],
        }
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            report_path = str(Path(out_dir) / "il.exec.report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(emergency_report, f, indent=2, ensure_ascii=False, allow_nan=False)
            log(f"OK: wrote emergency report to {out_dir}/il.exec.report.json")
        except Exception as we:
            log(f"ERROR: failed to write emergency report: {we}")


if __name__ == "__main__":
    main()
