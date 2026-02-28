#!/usr/bin/env python3
"""
S31-05: IL doctor entrypoint.

Runs lightweight health checks for IL workflow in stopless mode.
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


repo_root = Path(__file__).resolve().parent.parent


def usage() -> str:
    return "python3 scripts/il_doctor.py [--out <dir>]"


def _resolve_path(text: str) -> Path:
    p = Path(text).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def parse_args(args: List[str]) -> Tuple[Path, List[str], bool]:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = repo_root / ".local" / "obs" / f"il_doctor_{ts}"
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return out, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out = _resolve_path(args[i + 1])
            i += 2
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    return out, errors, False


def _run(cmd: List[str], cwd: Path) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except Exception as exc:
        return 1, str(exc)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def run_doctor(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: List[Dict[str, object]] = []

    checks = [
        (
            "workspace_init",
            [
                "python3",
                str(repo_root / "scripts" / "il_workspace_init.py"),
                "--out",
                str(out_dir / "workspace"),
                "--force",
            ],
            ["OK: workspace_initialized"],
        ),
        (
            "lint_fixture",
            [
                "python3",
                str(repo_root / "scripts" / "il_lint.py"),
                "--il",
                str(repo_root / "tests" / "fixtures" / "il_exec" / "il_min.json"),
                "--out",
                str(out_dir / "lint.report.json"),
            ],
            ["OK: lint_status=OK"],
        ),
        (
            "compile_entry_smoke",
            ["python3", str(repo_root / "scripts" / "il_compile_entry_smoke.py")],
            ["OK: smoke_summary STOP=0"],
        ),
        (
            "thread_smoke",
            [
                "python3",
                str(repo_root / "scripts" / "il_thread_runner_v2_smoke.py"),
                "--out",
                str(out_dir / "thread_smoke"),
            ],
            ["OK: smoke_summary STOP=0"],
        ),
    ]

    for name, cmd, expected in checks:
        rc, output = _run(cmd, repo_root)
        (out_dir / f"{name}.log").write_text(output, encoding="utf-8")
        ok = rc == 0 and all(mark in output for mark in expected)
        steps.append({"name": name, "rc": rc, "status": "OK" if ok else "ERROR"})
        if ok:
            print(f"OK: doctor_step={name} status=OK")
        else:
            print(f"ERROR: doctor_step={name} status=ERROR")

    overall_ok = all(step["status"] == "OK" for step in steps)
    summary = {
        "schema": "IL_DOCTOR_REPORT_v1",
        "status": "OK" if overall_ok else "ERROR",
        "out_dir": str(out_dir),
        "steps": steps,
    }
    (out_dir / "il.doctor.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if overall_ok:
        print("OK: il_doctor_summary status=OK")
        return 0
    print("ERROR: il_doctor_summary status=ERROR")
    return 1


def main(argv: List[str]) -> int:
    out, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_doctor(out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
