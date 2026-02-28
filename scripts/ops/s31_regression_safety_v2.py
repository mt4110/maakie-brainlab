#!/usr/bin/env python3
"""
S31-22: IL regression safety v2.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List


TESTS = [
    "tests/test_il_compile.py",
    "tests/test_il_validator.py",
    "tests/test_il_thread_runner_v2.py",
]


def _run(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except Exception as exc:
        return {"status": "ERROR", "returncode": 1, "reason": str(exc)}
    output = (proc.stdout or "") + (proc.stderr or "")
    return {
        "status": "PASS" if proc.returncode == 0 else "WARN",
        "returncode": proc.returncode,
        "output_tail": output[-800:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s31-22")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["python3", "-m", "unittest", "-v", *TESTS]
    row = _run(cmd, repo_root)

    payload = {
        "schema": "S31_REGRESSION_SAFETY_V2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": row.get("status", "WARN"),
        "tests": TESTS,
        "result": row,
    }
    (out_dir / "regression_safety_v2_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "regression_safety_v2_latest.md").write_text(
        "# S31-22 Regression Safety v2\n\n"
        f"- status: `{payload['status']}`\n"
        f"- returncode: `{row.get('returncode', -1)}`\n",
        encoding="utf-8",
    )

    print(f"OK: s31_regression_safety_v2 status={payload['status']}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
