#!/usr/bin/env python3
"""
S31-29: closeout generator.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s31-29")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    acceptance = _read_json((repo_root / "docs/evidence/s31-21/acceptance_wall_v5_latest.json").resolve())
    regression = _read_json((repo_root / "docs/evidence/s31-22/regression_safety_v2_latest.json").resolve())
    reliability = _read_json((repo_root / "docs/evidence/s31-23/reliability_soak_v2_latest.json").resolve())
    drift = _read_json((repo_root / "docs/evidence/s31-24/policy_drift_guard_latest.json").resolve())
    trend = _read_json((repo_root / "docs/evidence/s31-25/evidence_trend_index_v6_latest.json").resolve())

    statuses = {
        "acceptance": str(acceptance.get("status", "WARN")),
        "regression": str(regression.get("status", "WARN")),
        "reliability": str(reliability.get("status", "WARN")),
        "policy_drift": str(drift.get("status", "WARN")),
        "trend": str(trend.get("status", "WARN")),
    }
    pass_count = sum(1 for v in statuses.values() if v == "PASS")
    overall = "PASS" if pass_count == len(statuses) else "WARN"

    payload = {
        "schema": "S31_CLOSEOUT_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": overall,
        "statuses": statuses,
        "summary": {
            "checks_total": len(statuses),
            "checks_pass": pass_count,
            "checks_warn": len(statuses) - pass_count,
        },
        "unresolved_risks": [
            "RAG opcode bridge still relies on fixture-centric deterministic flow.",
            "local_llm quality variability remains outside deterministic compile contract.",
        ],
    }

    (out_dir / "closeout_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "closeout_latest.md").write_text(
        "# S31 Closeout\n\n"
        f"- status: `{overall}`\n"
        f"- checks_pass: `{pass_count}/{len(statuses)}`\n",
        encoding="utf-8",
    )

    print(f"OK: s31_closeout status={overall} pass={pass_count}/{len(statuses)}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
