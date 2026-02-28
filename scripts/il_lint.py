#!/usr/bin/env python3
"""
S31-04: IL lint CLI.

Checks IL contract compliance and emits structured report.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.il_validator import ILValidator


def usage() -> str:
    return "python3 scripts/il_lint.py --il <file> [--out <report.json>] [--strict]"


def parse_args(args: List[str]) -> Tuple[Optional[Path], Optional[Path], bool, List[str], bool]:
    il_path: Optional[Path] = None
    out_path: Optional[Path] = None
    strict = False
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return il_path, out_path, strict, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--il":
            if i + 1 >= len(args):
                errors.append("missing value for --il")
                i += 1
                continue
            il_path = Path(args[i + 1]).expanduser()
            i += 2
        elif token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out_path = Path(args[i + 1]).expanduser()
            i += 2
        elif token == "--strict":
            strict = True
            i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    if il_path is None:
        errors.append("missing required --il")

    if il_path is not None and not il_path.is_absolute():
        il_path = (repo_root / il_path).resolve()
    if out_path is not None and not out_path.is_absolute():
        out_path = (repo_root / out_path).resolve()

    return il_path, out_path, strict, errors, False


def _report(status: str, il_path: str, errors: List[Dict[str, Any]], strict: bool) -> Dict[str, Any]:
    code_hist: Dict[str, int] = {}
    for err in errors:
        code = str(err.get("code", ""))
        if code:
            code_hist[code] = code_hist.get(code, 0) + 1
    return {
        "schema": "IL_LINT_REPORT_v1",
        "status": status,
        "strict": strict,
        "il_path": il_path,
        "error_count": len(errors),
        "error_codes": dict(sorted(code_hist.items(), key=lambda kv: kv[0])),
        "errors": errors,
    }


def run_lint(il_path: Path, out_path: Optional[Path], strict: bool) -> int:
    if not il_path.exists():
        errors = [{"code": "E_INPUT", "message": f"file not found: {il_path}", "path": "/"}]
        report = _report("ERROR", str(il_path), errors, strict)
        print(f"ERROR: file_not_found path={il_path}")
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    try:
        obj = json.loads(il_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors = [{"code": "E_PARSE", "message": f"json parse failed: {exc}", "path": "/"}]
        report = _report("ERROR", str(il_path), errors, strict)
        print(f"ERROR: json_parse_failed path={il_path} reason={exc}")
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    validator = ILValidator()
    valid, val_errors = validator.validate(obj)
    status = "OK" if valid else "ERROR"
    report = _report(status, str(il_path), val_errors, strict)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if valid:
        print(f"OK: lint_status=OK path={il_path}")
        print("OK: lint_summary errors=0")
        return 0

    for err in val_errors:
        code = err.get("code", "")
        path = err.get("path", "")
        message = err.get("message", "")
        hint = err.get("hint", "")
        print(f"ERROR: code={code} path={path} message={message} hint={hint}")
    print(f"ERROR: lint_summary errors={len(val_errors)}")
    return 1


def main(argv: List[str]) -> int:
    il_path, out_path, strict, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    if il_path is None:
        print("ERROR: missing required --il")
        print(f"OK: usage: {usage()}")
        return 1
    return run_lint(il_path=il_path, out_path=out_path, strict=strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
