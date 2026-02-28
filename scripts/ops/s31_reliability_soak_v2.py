#!/usr/bin/env python3
"""
S31-23: reliability soak v2 for il_thread_runner_v2.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List


def _run_once(repo_root: Path, out_dir: Path) -> Dict[str, object]:
    cmd = [
        "python3",
        "scripts/il_thread_runner_v2_replay_check.py",
        "--mode",
        "validate-only",
        "--out",
        str(out_dir),
    ]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + (proc.stderr or "")
    report_path = out_dir / "il.thread.replay.report.json"
    match = False
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            match = bool(report.get("match", False))
        except Exception:
            match = False
    return {
        "returncode": proc.returncode,
        "match": match,
        "ok": proc.returncode == 0 and match,
        "output_tail": output[-500:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s31-23")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    runs = max(1, int(args.runs))
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for i in range(1, runs + 1):
            run_out = base / f"run_{i:02d}"
            row = _run_once(repo_root, run_out)
            row["run"] = i
            rows.append(row)

    pass_count = sum(1 for r in rows if bool(r.get("ok", False)))
    status = "PASS" if pass_count == runs else "WARN"

    payload = {
        "schema": "S31_RELIABILITY_SOAK_V2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "metrics": {
            "total_runs": runs,
            "pass_runs": pass_count,
            "pass_rate": pass_count / runs,
        },
        "runs": rows,
    }

    (out_dir / "reliability_soak_v2_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "reliability_soak_v2_latest.md").write_text(
        "# S31-23 Reliability Soak v2\n\n"
        f"- status: `{status}`\n"
        f"- total_runs: `{runs}`\n"
        f"- pass_runs: `{pass_count}`\n"
        f"- pass_rate: `{pass_count / runs:.3f}`\n",
        encoding="utf-8",
    )

    print(f"OK: s31_reliability_soak_v2 status={status} pass={pass_count}/{runs}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
