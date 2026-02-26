"""
S23-10: integrated closeout suite for il_thread_runner_v2.
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.il_thread_runner_v2 import run_thread_runner
from scripts.il_thread_runner_v2_doctor import run_doctor
from scripts.il_thread_runner_v2_replay_check import run_replay_check


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return (
        "python3 scripts/il_thread_runner_v2_suite.py "
        "[--cases <jsonl>] [--out <dir>]"
    )


def _resolve_path(text: str) -> Path:
    p = Path(text).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def parse_args(args: List[str]) -> Tuple[Path, Path, List[str], bool]:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cases = repo_root / "tests" / "fixtures" / "il_thread_runner" / "cases_smoke.jsonl"
    out = repo_root / ".local" / "obs" / f"il_thread_runner_v2_suite_{ts}"
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return cases, out, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--cases":
            if i + 1 >= len(args):
                errors.append("missing value for --cases")
                i += 1
                continue
            cases = _resolve_path(args[i + 1])
            i += 2
        elif token == "--out":
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
    return cases, out, errors, False


def run_suite(cases: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    steps: List[Dict[str, object]] = []
    log("OK", f"phase=boot out={out} cases={cases}")

    validate_run_dir = out / "validate_run"
    rc_validate = run_thread_runner(
        cases_path=cases,
        mode="validate-only",
        out_dir=validate_run_dir,
    )
    steps.append({"name": "validate_run", "rc": rc_validate, "status": "OK" if rc_validate == 0 else "ERROR"})
    if rc_validate == 0:
        log("OK", "phase=step name=validate_run status=OK")
    else:
        log("ERROR", "phase=step name=validate_run status=ERROR")

    rc_doctor = run_doctor(validate_run_dir)
    steps.append({"name": "doctor", "rc": rc_doctor, "status": "OK" if rc_doctor == 0 else "ERROR"})
    if rc_doctor == 0:
        log("OK", "phase=step name=doctor status=OK")
    else:
        log("ERROR", "phase=step name=doctor status=ERROR")

    replay_dir = out / "replay"
    rc_replay = run_replay_check(
        cases=cases,
        out=replay_dir,
        mode="validate-only",
        provider="rule_based",
        model="rule_based_v1",
        prompt_profile="v1",
        seed=7,
        allow_fallback=True,
        entry_timeout_sec=30,
        entry_script=repo_root / "scripts" / "il_entry.py",
    )
    steps.append({"name": "replay_check", "rc": rc_replay, "status": "OK" if rc_replay == 0 else "ERROR"})
    if rc_replay == 0:
        log("OK", "phase=step name=replay_check status=OK")
    else:
        log("ERROR", "phase=step name=replay_check status=ERROR")

    smoke_cmd = ["python3", str(repo_root / "scripts" / "il_thread_runner_v2_smoke.py")]
    smoke_proc = subprocess.run(
        smoke_cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    smoke_output = (smoke_proc.stdout or "") + (smoke_proc.stderr or "")
    (out / "thread_smoke.log").write_text(smoke_output, encoding="utf-8")
    rc_smoke = 1
    if smoke_proc.returncode == 0 and "OK: smoke_summary STOP=0" in smoke_output:
        rc_smoke = 0
    steps.append({"name": "thread_smoke", "rc": rc_smoke, "status": "OK" if rc_smoke == 0 else "ERROR"})
    if rc_smoke == 0:
        log("OK", "phase=step name=thread_smoke status=OK")
    else:
        log("ERROR", "phase=step name=thread_smoke status=ERROR")

    overall_ok = all(int(step.get("rc", 1)) == 0 for step in steps)
    summary = {
        "schema": "IL_THREAD_V2_SUITE_v1",
        "status": "OK" if overall_ok else "ERROR",
        "cases": str(cases),
        "out": str(out),
        "steps": steps,
    }
    summary_path = out / "suite.summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if overall_ok:
        log("OK", "suite_summary status=OK")
        return 0
    log("ERROR", "suite_summary status=ERROR")
    return 1


def main(argv: List[str]) -> int:
    cases, out, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_suite(cases, out)


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_thread_runner_v2_suite unexpected exception: {exc}")
        rc = 1
    if rc == 0:
        print("OK: il_thread_runner_v2_suite exit=0")
    else:
        print("ERROR: il_thread_runner_v2_suite exit=1")
    sys.exit(rc)
