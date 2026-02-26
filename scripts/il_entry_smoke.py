"""
S22-16: IL entry smoke for verify-il canonical path.

Lightweight and stopless:
- good fixture expects "OK: phase=end STOP=0"
- bad fixture expects "OK: phase=end STOP=1"
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def run_case(
    repo_root: Path,
    il_entry_path: Path,
    case_name: str,
    il_path: Path,
    fixture_db: Optional[Path],
    expected_final_line: str,
) -> int:
    stop = 0
    cmd = ["python3", str(il_entry_path), str(il_path)]
    if fixture_db:
        cmd += ["--fixture-db", str(fixture_db)]

    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if output.strip():
            print(output.rstrip())

        if proc.returncode != 0:
            log("ERROR", f"case={case_name} non_zero_returncode={proc.returncode}")
            stop = 1

        if expected_final_line in output:
            log("OK", f"case={case_name} matched='{expected_final_line}'")
        else:
            log("ERROR", f"case={case_name} missing='{expected_final_line}'")
            stop = 1
    except Exception as exc:
        log("ERROR", f"case={case_name} exception={exc}")
        stop = 1

    return stop


def run_smoke() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    il_entry_path = repo_root / "scripts" / "il_entry.py"
    fixture_dir = repo_root / "tests" / "fixtures" / "il_exec"
    obs_dir = repo_root / ".local" / "obs" / "il_entry_smoke"
    obs_dir.mkdir(parents=True, exist_ok=True)

    bad_fixture = obs_dir / "bad_schema.json"
    try:
        bad_fixture.write_text('{"invalid":"format"}\n', encoding="utf-8")
        log("OK", f"prepared_bad_fixture={bad_fixture}")
    except Exception as exc:
        log("ERROR", f"cannot_write_bad_fixture err={exc}")
        log("ERROR", "smoke_summary STOP=1 cases=0 passed=0 failed=1")
        return

    cases = [
        {
            "name": "good_minimal",
            "il": fixture_dir / "il_min.json",
            "db": fixture_dir / "retrieve_db.json",
            "expect": "OK: phase=end STOP=0",
        },
        {
            "name": "bad_schema",
            "il": bad_fixture,
            "db": None,
            "expect": "OK: phase=end STOP=1",
        },
    ]

    total = 0
    failed = 0
    for case in cases:
        total += 1
        log("OK", f"start_case={case['name']}")
        case_stop = run_case(
            repo_root=repo_root,
            il_entry_path=il_entry_path,
            case_name=case["name"],
            il_path=case["il"],
            fixture_db=case["db"],
            expected_final_line=case["expect"],
        )
        if case_stop == 0:
            log("OK", f"end_case={case['name']} STOP=0")
        else:
            log("ERROR", f"end_case={case['name']} STOP=1")
            failed += 1

    passed = total - failed
    if failed == 0:
        log("OK", f"smoke_summary STOP=0 cases={total} passed={passed} failed={failed}")
    else:
        log("ERROR", f"smoke_summary STOP=1 cases={total} passed={passed} failed={failed}")


if __name__ == "__main__":
    run_smoke()
