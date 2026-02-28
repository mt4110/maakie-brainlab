#!/usr/bin/env python3
"""
S31-25: evidence trend index v6 for S31.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List


INPUTS = {
    "s31-21": "docs/evidence/s31-21/acceptance_wall_v5_latest.json",
    "s31-22": "docs/evidence/s31-22/regression_safety_v2_latest.json",
    "s31-23": "docs/evidence/s31-23/reliability_soak_v2_latest.json",
    "s31-24": "docs/evidence/s31-24/policy_drift_guard_latest.json",
}


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s31-25")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []
    for phase, rel in INPUTS.items():
        path = (repo_root / rel).resolve()
        obj = _read_json(path)
        if obj:
            rows.append({"phase": phase, "status": str(obj.get("status", "WARN")), "path": rel, "missing": False})
        else:
            rows.append({"phase": phase, "status": "WARN", "path": rel, "missing": True})

    missing_count = sum(1 for r in rows if bool(r.get("missing", False)))
    warn_count = sum(1 for r in rows if str(r.get("status", "WARN")) != "PASS")
    status = "PASS" if warn_count == 0 else "WARN"

    payload = {
        "schema": "S31_EVIDENCE_TREND_INDEX_V6",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "summary": {
            "phase_total": len(rows),
            "missing_count": missing_count,
            "warn_count": warn_count,
        },
        "rows": rows,
    }

    (out_dir / "evidence_trend_index_v6_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    md = ["# S31-25 Evidence Trend Index v6", "", f"- status: `{status}`", "", "| phase | status | missing | path |", "|---|---|---:|---|"]
    for row in rows:
        md.append(
            "| {phase} | {status} | {missing} | `{path}` |".format(
                phase=row["phase"],
                status=row["status"],
                missing="yes" if row["missing"] else "no",
                path=row["path"],
            )
        )
    (out_dir / "evidence_trend_index_v6_latest.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")

    history_path = out_dir / "evidence_trend_history_v6.json"
    history = []
    if history_path.exists():
        try:
            old = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(old, list):
                history = old
        except Exception:
            history = []
    history.append(
        {
            "captured_at_utc": payload["captured_at_utc"],
            "status": status,
            "summary": payload["summary"],
        }
    )
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK: s31_evidence_trend_index_v6 status={status} warn={warn_count}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
