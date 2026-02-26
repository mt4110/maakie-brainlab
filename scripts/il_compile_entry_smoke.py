"""
S23-03 smoke:
1) compile natural language request into IL
2) feed compiled IL to il_entry

Stopless, grep-friendly logs only.
"""

import json
import os
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
            env=os.environ.copy(),
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


def run_smoke() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    compile_script = repo_root / "scripts" / "il_compile.py"
    il_entry_script = repo_root / "scripts" / "il_entry.py"
    fixture_db = repo_root / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

    run_id = int(time.time() * 1000)
    obs_root = repo_root / ".local" / "obs" / f"il_compile_entry_smoke_{run_id}"
    obs_root.mkdir(parents=True, exist_ok=True)

    request_path = obs_root / "compile.request.json"
    compile_out = obs_root / "compile_out"
    exec_out = obs_root / "exec_out"
    compiled_path = compile_out / "il.compiled.json"

    request_payload = {
        "schema": "IL_COMPILE_REQUEST_v1",
        "request_text": "Find alpha and beta overview in greek docs",
        "context": {"keywords": ["alpha", "beta", "greek"]},
        "constraints": {
            "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
            "forbidden_keys": [],
            "max_steps": 4,
        },
        "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
        "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
    }
    try:
        request_path.write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        log("ERROR", f"cannot_write_request exception={exc}")
        log("ERROR", "smoke_summary STOP=1 cases=2 passed=0 failed=2")
        return

    failed = 0
    total = 2

    log("OK", "start_case=compile")
    compile_cmd = [
        "python3",
        str(compile_script),
        "--request",
        str(request_path),
        "--out",
        str(compile_out),
    ]
    stop, compile_output = _run(compile_cmd, repo_root, "compile")
    if stop == 0 and "OK: phase=end STOP=0" in compile_output and compiled_path.exists():
        log("OK", f"end_case=compile STOP=0 compiled={compiled_path}")
    else:
        log("ERROR", "end_case=compile STOP=1")
        failed += 1

    log("OK", "start_case=entry")
    entry_cmd = [
        "python3",
        str(il_entry_script),
        str(compiled_path),
        "--out",
        str(exec_out),
        "--fixture-db",
        str(fixture_db),
    ]
    stop, entry_output = _run(entry_cmd, repo_root, "entry")
    if stop == 0 and "OK: phase=end STOP=0" in entry_output:
        log("OK", "end_case=entry STOP=0")
    else:
        log("ERROR", "end_case=entry STOP=1")
        failed += 1

    passed = total - failed
    if failed == 0:
        log("OK", f"smoke_summary STOP=0 cases={total} passed={passed} failed={failed}")
    else:
        log("ERROR", f"smoke_summary STOP=1 cases={total} passed={passed} failed={failed}")


if __name__ == "__main__":
    run_smoke()
