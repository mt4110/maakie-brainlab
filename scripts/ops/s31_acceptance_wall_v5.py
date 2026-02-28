#!/usr/bin/env python3
"""
S31-21: IL acceptance wall v5.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List


def _run(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc), "returncode": 1}
    output = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0
    return {
        "status": "PASS" if ok else "WARN",
        "returncode": proc.returncode,
        "output_tail": output[-600:],
    }


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, obj: Dict[str, Any]) -> None:
    checks = obj.get("checks", [])
    lines = ["# S31-21 Acceptance Wall v5", "", f"- status: `{obj.get('status', '')}`", "", "## Checks", ""]
    for row in checks:
        lines.append(
            "- [{status}] {id} `{cmd}` rc={rc}".format(
                status=row.get("status", "WARN"),
                id=row.get("id", ""),
                cmd=row.get("cmd", ""),
                rc=row.get("returncode", -1),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s31-21")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()

    checks_spec = [
        ("ACC-01", ["python3", "scripts/il_lint.py", "--il", "tests/fixtures/il_exec/il_min.json"]),
        ("ACC-02", ["python3", "scripts/il_compile_entry_smoke.py"]),
        ("ACC-03", ["python3", "scripts/il_thread_runner_v2_smoke.py", "--out", str(out_dir / "thread_smoke")]),
    ]

    checks: List[Dict[str, Any]] = []
    for cid, cmd in checks_spec:
        result = _run(cmd, repo_root)
        checks.append({"id": cid, "cmd": " ".join(cmd), **result})

    pass_count = sum(1 for c in checks if c.get("status") == "PASS")
    status = "PASS" if pass_count == len(checks) else "WARN"

    payload = {
        "schema": "S31_ACCEPTANCE_WALL_V5",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "summary": {
            "total": len(checks),
            "pass": pass_count,
            "warn": len(checks) - pass_count,
        },
        "checks": checks,
    }

    _write_json(out_dir / "acceptance_wall_v5_latest.json", payload)
    _write_md(out_dir / "acceptance_wall_v5_latest.md", payload)

    print(f"OK: s31_acceptance_wall_v5 status={status} pass={pass_count}/{len(checks)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
