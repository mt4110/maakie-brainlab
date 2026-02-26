"""
S23-04 smoke:
- validate-only mode must skip entry execution
- run mode must execute entry for compile-success cases
"""

import json
import subprocess
import time
from pathlib import Path


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


def run_smoke() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    runner_script = repo_root / "scripts" / "il_thread_runner_v2.py"

    run_id = int(time.time() * 1000)
    obs_root = repo_root / ".local" / "obs" / f"il_thread_runner_v2_smoke_{run_id}"
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
    else:
        log("ERROR", f"smoke_summary STOP=1 cases={total} passed={passed} failed={failed}")


if __name__ == "__main__":
    run_smoke()
