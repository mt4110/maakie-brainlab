#!/usr/bin/env python3
"""
S32-17: acceptance wall v6.
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
        return {"status": "ERROR", "returncode": 1, "reason": str(exc)}
    output = (proc.stdout or "") + (proc.stderr or "")
    return {
        "status": "PASS" if proc.returncode == 0 else "WARN",
        "returncode": proc.returncode,
        "output_tail": output[-800:],
    }


def _check_file_contains(path: Path, pattern: str) -> Dict[str, Any]:
    if not path.exists():
        return {"status": "WARN", "reason": f"missing_file:{path}"}
    text = path.read_text(encoding="utf-8")
    return {"status": "PASS" if pattern in text else "WARN", "reason": f"pattern={pattern}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-17")
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    checks: List[Dict[str, Any]] = []
    file_checks = [
        ("ACC-S32-01-04", repo_root / "src" / "il_executor.py", "E_RAG_POLICY_DENYLIST"),
        ("ACC-S32-07", repo_root / "src" / "il_compile.py", "confidence_status"),
        ("ACC-S32-08", repo_root / "src" / "il_compile.py", "repair_rule_id"),
        ("ACC-S32-11", repo_root / "scripts" / "il_thread_runner_v2_orchestrator.py", "run_orchestrator"),
        ("ACC-S32-15", repo_root / "scripts" / "ops" / "s32_operator_dashboard_export.py", "S32_OPERATOR_DASHBOARD_V1"),
        ("ACC-S32-16", repo_root / "scripts" / "ops" / "s32_latency_slo_guard.py", "S32_LATENCY_SLO_GUARD_V1"),
    ]
    for cid, path, pattern in file_checks:
        result = _check_file_contains(path, pattern)
        checks.append({"id": cid, "type": "file_contains", "path": str(path), **result})

    if not args.skip_commands:
        command_checks = [
            ("ACC-CMD-07", ["python3", "-m", "unittest", "-v", "tests/test_s32_compile_confidence_contract.py"]),
            ("ACC-CMD-11", ["python3", "-m", "unittest", "-v", "tests/test_s32_runner_shard_orchestrator.py"]),
            ("ACC-CMD-16", ["python3", "-m", "unittest", "-v", "tests/test_s32_latency_slo_guard.py"]),
        ]
        for cid, cmd in command_checks:
            result = _run(cmd, repo_root)
            checks.append({"id": cid, "type": "command", "cmd": " ".join(cmd), **result})

    pass_count = sum(1 for c in checks if c.get("status") == "PASS")
    warn_count = sum(1 for c in checks if c.get("status") == "WARN")
    error_count = sum(1 for c in checks if c.get("status") == "ERROR")
    status = "PASS" if warn_count == 0 and error_count == 0 else ("ERROR" if error_count > 0 else "WARN")

    payload = {
        "schema": "S32_ACCEPTANCE_WALL_V6",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "summary": {
            "total": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "error": error_count,
        },
        "checks": checks,
    }

    (out_dir / "acceptance_wall_v6_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# S32-17 Acceptance Wall v6",
        "",
        f"- status: `{status}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        if row.get("type") == "command":
            lines.append(
                "- [{status}] {id} `{cmd}` rc={rc}".format(
                    status=row.get("status", "WARN"),
                    id=row.get("id", ""),
                    cmd=row.get("cmd", ""),
                    rc=row.get("returncode", -1),
                )
            )
        else:
            lines.append(
                "- [{status}] {id} `{path}` ({reason})".format(
                    status=row.get("status", "WARN"),
                    id=row.get("id", ""),
                    path=row.get("path", ""),
                    reason=row.get("reason", ""),
                )
            )
    (out_dir / "acceptance_wall_v6_latest.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"OK: s32_acceptance_wall_v6 status={status} pass={pass_count}/{len(checks)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
