"""
S23-04 smoke:
- validate-only mode must skip entry execution
- run mode must execute entry for compile-success cases
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def _run(cmd: list[str], cwd: Path, case_name: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if output.strip():
            print(output.rstrip())
        if proc.returncode != 0:
            log("ERROR", f"case={case_name} returncode={proc.returncode}")
            return 1, output
        return 0, output
    except Exception as exc:
        log("ERROR", f"case={case_name} exception={exc}")
        return 1, ""


def _write_cases(path: Path) -> None:
    rows = [
        {
            "id": "smoke_alpha",
            "request": {
                "schema": "IL_COMPILE_REQUEST_v1",
                "request_text": "Find alpha overview in greek docs",
                "context": {"keywords": ["alpha", "greek"]},
                "constraints": {
                    "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                    "forbidden_keys": [],
                    "max_steps": 4,
                },
                "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
                "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
            },
            "fixture_db": "tests/fixtures/il_exec/retrieve_db.json",
        },
        {
            "id": "smoke_beta",
            "request": {
                "schema": "IL_COMPILE_REQUEST_v1",
                "request_text": "Retrieve beta note",
                "context": {"keywords": ["beta"]},
                "constraints": {
                    "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "CITE"],
                    "forbidden_keys": [],
                    "max_steps": 3,
                },
                "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
                "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
            },
            "fixture_db": "tests/fixtures/il_exec/retrieve_db.json",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def usage() -> str:
    return "python3 scripts/il_thread_runner_v2_smoke.py [--out <dir>]"


def parse_args(args: List[str]) -> Tuple[Optional[Path], List[str], bool]:
    out_dir: Optional[Path] = None
    errors: List[str] = []
    if "--help" in args or "-h" in args:
        return out_dir, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out_dir = Path(args[i + 1]).expanduser()
            i += 2
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1
    return out_dir, errors, False


def run_smoke(out_dir: Optional[Path] = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    runner_script = repo_root / "scripts" / "il_thread_runner_v2.py"

    if out_dir is None:
        run_id = int(time.time() * 1000)
        obs_root = repo_root / ".local" / "obs" / f"il_thread_runner_v2_smoke_{run_id}"
    else:
        obs_root = out_dir if out_dir.is_absolute() else (repo_root / out_dir).resolve()
    cases_path = obs_root / "cases.jsonl"
    validate_out = obs_root / "validate_only"
    run_out = obs_root / "run_mode"

    _write_cases(cases_path)

    failed = 0
    total = 2

    log("OK", "start_case=validate_only")
    stop, _ = _run(
        [
            "python3",
            str(runner_script),
            "--cases",
            str(cases_path),
            "--mode",
            "validate-only",
            "--out",
            str(validate_out),
        ],
        repo_root,
        "validate_only",
    )
    if stop == 0 and (validate_out / "summary.json").exists():
        summary = json.loads((validate_out / "summary.json").read_text(encoding="utf-8"))
        if summary.get("entry_skip_count") == 2 and summary.get("entry_ok_count") == 0:
            log("OK", "end_case=validate_only STOP=0")
        else:
            log("ERROR", f"end_case=validate_only bad_summary={summary}")
            failed += 1
    else:
        log("ERROR", "end_case=validate_only STOP=1")
        failed += 1

    log("OK", "start_case=run_mode")
    stop, _ = _run(
        [
            "python3",
            str(runner_script),
            "--cases",
            str(cases_path),
            "--mode",
            "run",
            "--out",
            str(run_out),
        ],
        repo_root,
        "run_mode",
    )
    if stop == 0 and (run_out / "summary.json").exists():
        summary = json.loads((run_out / "summary.json").read_text(encoding="utf-8"))
        if summary.get("entry_ok_count") == 2 and summary.get("entry_error_count") == 0:
            log("OK", "end_case=run_mode STOP=0")
        else:
            log("ERROR", f"end_case=run_mode bad_summary={summary}")
            failed += 1
    else:
        log("ERROR", "end_case=run_mode STOP=1")
        failed += 1

    passed = total - failed
    if failed == 0:
        log("OK", f"smoke_summary STOP=0 cases={total} passed={passed} failed={failed}")
        return 0
    log("ERROR", f"smoke_summary STOP=1 cases={total} passed={passed} failed={failed}")
    return 1


def main(args: List[str]) -> int:
    out_dir, errors, show_help = parse_args(args)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_smoke(out_dir=out_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
