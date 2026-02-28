#!/usr/bin/env python3
"""
S31-26: Unified IL CLI wrapper.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List


repo_root = Path(__file__).resolve().parent.parent


COMMAND_MAP: Dict[str, List[str]] = {
    "init": ["python3", str(repo_root / "scripts" / "il_workspace_init.py")],
    "fmt": ["python3", str(repo_root / "scripts" / "il_fmt.py")],
    "lint": ["python3", str(repo_root / "scripts" / "il_lint.py")],
    "compile": ["python3", str(repo_root / "scripts" / "il_compile.py")],
    "entry": ["python3", str(repo_root / "scripts" / "il_entry.py")],
    "thread": ["python3", str(repo_root / "scripts" / "il_thread_runner_v2.py")],
    "doctor": ["python3", str(repo_root / "scripts" / "il_doctor.py")],
}


def usage() -> str:
    cmds = ", ".join(sorted(COMMAND_MAP.keys()))
    return (
        "python3 scripts/ilctl.py <command> [args...]\n"
        f"commands: {cmds}\n"
        "examples:\n"
        "  python3 scripts/ilctl.py init --out .local/obs/il_ws\n"
        "  python3 scripts/ilctl.py fmt --check docs/il/examples/good_min.json\n"
        "  python3 scripts/ilctl.py compile --request req.json --out .local/obs/compile"
    )


def main(argv: List[str]) -> int:
    if not argv or argv[0] in {"--help", "-h", "help"}:
        print(f"OK: usage:\n{usage()}")
        return 0

    command = argv[0].strip().lower()
    if command not in COMMAND_MAP:
        print(f"ERROR: unknown command: {command}")
        print(f"OK: usage:\n{usage()}")
        return 1

    cmd = COMMAND_MAP[command] + argv[1:]
    try:
        proc = subprocess.run(cmd, cwd=repo_root, check=False)
    except Exception as exc:
        print(f"ERROR: ilctl command failed: {exc}")
        return 1

    if proc.returncode == 0:
        print(f"OK: ilctl command={command} exit=0")
        return 0
    print(f"ERROR: ilctl command={command} exit={proc.returncode}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
