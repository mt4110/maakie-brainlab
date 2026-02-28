#!/usr/bin/env python3
"""
S31-26: Unified IL CLI wrapper.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


repo_root = Path(__file__).resolve().parent.parent
PYTHON = sys.executable or "python3"


COMMAND_MAP: Dict[str, List[str]] = {
    "init": [PYTHON, str(repo_root / "scripts" / "il_workspace_init.py")],
    "fmt": [PYTHON, str(repo_root / "scripts" / "il_fmt.py")],
    "lint": [PYTHON, str(repo_root / "scripts" / "il_lint.py")],
    "compile": [PYTHON, str(repo_root / "scripts" / "il_compile.py")],
    "entry": [PYTHON, str(repo_root / "scripts" / "il_entry.py")],
    "thread": [PYTHON, str(repo_root / "scripts" / "il_thread_runner_v2.py")],
    "doctor": [PYTHON, str(repo_root / "scripts" / "il_doctor.py")],
}

SCENARIO_COMMANDS = ["quickstart", "triage", "verify-pack"]


def usage() -> str:
    cmds = ", ".join(sorted(COMMAND_MAP.keys()))
    scenarios = ", ".join(SCENARIO_COMMANDS)
    return (
        "python3 scripts/ilctl.py <command> [args...]\n"
        f"commands: {cmds}\n"
        f"scenarios: {scenarios}\n"
        "examples:\n"
        "  python3 scripts/ilctl.py init --out .local/obs/il_ws\n"
        "  python3 scripts/ilctl.py quickstart --out .local/obs/il_ws --force\n"
        "  python3 scripts/ilctl.py triage --out .local/obs/il_doctor\n"
        "  python3 scripts/ilctl.py verify-pack\n"
        "  python3 scripts/ilctl.py fmt --check docs/il/examples/good_min.json\n"
        "  python3 scripts/ilctl.py compile --request req.json --out .local/obs/compile"
    )


def _run(cmd: List[str], label: str) -> int:
    try:
        proc = subprocess.run(cmd, cwd=repo_root, check=False)
    except Exception as exc:
        print(f"ERROR: ilctl command failed: {exc}")
        return 1
    if proc.returncode == 0:
        print(f"OK: ilctl command={label} exit=0")
        return 0
    print(f"ERROR: ilctl command={label} exit={proc.returncode}")
    return 1


def _extract_out(args: List[str]) -> Optional[str]:
    for i, token in enumerate(args):
        if token == "--out" and i + 1 < len(args):
            return args[i + 1]
    return None


def _run_quickstart(args: List[str]) -> int:
    out = _extract_out(args)
    if not out:
        print("ERROR: quickstart requires --out <dir>")
        return 1

    init_cmd = COMMAND_MAP["init"] + args
    rc = _run(init_cmd, "quickstart:init")
    if rc != 0:
        return rc

    compile_out = str((Path(out).expanduser() / "out" / "compile"))
    entry_out = str((Path(out).expanduser() / "out" / "entry"))
    compile_cmd = COMMAND_MAP["compile"] + ["--request", str(Path(out) / "request.sample.json"), "--out", compile_out]
    rc = _run(compile_cmd, "quickstart:compile")
    if rc != 0:
        return rc
    entry_cmd = COMMAND_MAP["entry"] + [
        str(Path(compile_out) / "il.compiled.json"),
        "--out",
        entry_out,
        "--fixture-db",
        "tests/fixtures/il_exec/retrieve_db.json",
    ]
    return _run(entry_cmd, "quickstart:entry")


def _run_triage(args: List[str]) -> int:
    doctor_args = list(args)
    if "--out" not in doctor_args:
        doctor_args += ["--out", ".local/obs/il_doctor"]
    return _run(COMMAND_MAP["doctor"] + doctor_args, "triage")


def _run_verify_pack(args: List[str]) -> int:
    if args:
        print("ERROR: verify-pack does not accept extra args")
        return 1
    commands = [
        [PYTHON, str(repo_root / "scripts" / "il_compile_entry_smoke.py")],
        [PYTHON, str(repo_root / "scripts" / "il_thread_runner_v2_smoke.py")],
        [PYTHON, str(repo_root / "scripts" / "il_exec_selftest.py")],
    ]
    for idx, cmd in enumerate(commands, 1):
        rc = _run(cmd, f"verify-pack:{idx}")
        if rc != 0:
            return rc
    return 0


def main(argv: List[str]) -> int:
    if not argv or argv[0] in {"--help", "-h", "help"}:
        print(f"OK: usage:\n{usage()}")
        return 0

    command = argv[0].strip().lower()
    if command in SCENARIO_COMMANDS:
        if command == "quickstart":
            return _run_quickstart(argv[1:])
        if command == "triage":
            return _run_triage(argv[1:])
        return _run_verify_pack(argv[1:])

    if command not in COMMAND_MAP:
        print(f"ERROR: unknown command: {command}")
        print(f"OK: usage:\n{usage()}")
        return 1

    cmd = COMMAND_MAP[command] + argv[1:]
    return _run(cmd, command)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
