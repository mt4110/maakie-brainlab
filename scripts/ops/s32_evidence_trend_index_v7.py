#!/usr/bin/env python3
"""
S32-20: evidence trend index v7.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List


INPUTS = {
    "s32-05": "docs/evidence/s32-05/retrieval_eval_wall_latest.json",
    "s32-15": "docs/evidence/s32-15/operator_dashboard_latest.json",
    "s32-16": "docs/evidence/s32-16/latency_slo_guard_latest.json",
    "s32-17": "docs/evidence/s32-17/acceptance_wall_v6_latest.json",
    "s32-18": "docs/evidence/s32-18/policy_drift_guard_v2_latest.json",
    "s32-19": "docs/evidence/s32-19/reliability_soak_v3_latest.json",
}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _infer_status(obj: Dict[str, Any]) -> str:
    if not obj:
        return "WARN"
    summary = dict(obj.get("summary", {}))
    status = str(obj.get("status") or summary.get("status") or "").upper().strip()
    if status in {"PASS", "WARN", "ERROR"}:
        return status if status != "ERROR" else "WARN"
    readiness = str(summary.get("readiness") or "").upper().strip()
    if readiness == "READY":
        return "PASS"
    if readiness in {"CONDITIONAL_READY", "BLOCKED"}:
        return "WARN"
    return "WARN"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-20")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for phase, rel in INPUTS.items():
        path = (repo_root / rel).resolve()
        obj = _read_json(path)
        rows.append(
            {
                "phase": phase,
                "status": _infer_status(obj),
                "path": rel,
                "missing": not bool(obj),
            }
        )

    missing_count = sum(1 for r in rows if bool(r.get("missing")))
    warn_count = sum(1 for r in rows if str(r.get("status")) != "PASS")
    status = "PASS" if warn_count == 0 else "WARN"

    payload = {
        "schema": "S32_EVIDENCE_TREND_INDEX_V7",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "summary": {
            "phase_total": len(rows),
            "missing_count": missing_count,
            "warn_count": warn_count,
        },
        "rows": rows,
    }

    (out_dir / "evidence_trend_index_v7_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md = [
        "# S32-20 Evidence Trend Index v7",
        "",
        f"- status: `{status}`",
        "",
        "| phase | status | missing | path |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        md.append(
            "| {phase} | {status} | {missing} | `{path}` |".format(
                phase=row["phase"],
                status=row["status"],
                missing="yes" if row["missing"] else "no",
                path=row["path"],
            )
        )
    (out_dir / "evidence_trend_index_v7_latest.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")

    history_path = out_dir / "evidence_trend_history_v7.json"
    history: List[Dict[str, Any]] = []
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

    print(f"OK: s32_evidence_trend_index_v7 status={status} warn={warn_count}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
