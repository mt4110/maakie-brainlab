#!/usr/bin/env python3
"""
S32-26: regression safety v3 across S22/S23/S31/S32 contracts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List


MATRIX = [
    (
        "entry_law",
        ["python3", "-m", "unittest", "-v", "tests/test_il_validator.py"],
    ),
    (
        "compile_fail_closed",
        ["python3", "-m", "unittest", "-v", "tests/test_il_compile.py", "tests/test_s32_compile_parse_repair_v3.py"],
    ),
    (
        "runner_determinism",
        ["python3", "-m", "unittest", "-v", "tests/test_il_thread_runner_v2.py", "tests/test_s32_runner_shard_orchestrator.py"],
    ),
    (
        "collect_realism",
        ["python3", "-m", "unittest", "-v", "tests/test_s32_collect_non_fixture.py", "tests/test_s32_retrieval_ranking_v2.py"],
    ),
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
        "output_tail": output[-1200:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-26")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for axis, cmd in MATRIX:
        result = _run(cmd, repo_root)
        rows.append({"axis": axis, "cmd": " ".join(cmd), **result})

    pass_count = sum(1 for row in rows if row.get("status") == "PASS")
    status = "PASS" if pass_count == len(rows) else "WARN"
    payload = {
        "schema": "S32_REGRESSION_SAFETY_V3",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "summary": {
            "matrix_total": len(rows),
            "matrix_pass": pass_count,
            "matrix_warn": len(rows) - pass_count,
        },
        "matrix": rows,
    }

    (out_dir / "regression_safety_v3_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_lines = [
        "# S32-26 Regression Safety v3",
        "",
        f"- status: `{status}`",
        "",
        "| axis | status | returncode |",
        "|---|---|---:|",
    ]
    for row in rows:
        md_lines.append(
            "| {axis} | {status} | {rc} |".format(
                axis=row["axis"],
                status=row["status"],
                rc=row.get("returncode", -1),
            )
        )
    (out_dir / "regression_safety_v3_latest.md").write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    print(f"OK: s32_regression_safety_v3 status={status} pass={pass_count}/{len(rows)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
