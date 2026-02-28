#!/usr/bin/env python3
"""
S32-27: release readiness v2.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List


INPUTS = {
    "latency": "docs/evidence/s32-16/latency_slo_guard_latest.json",
    "acceptance": "docs/evidence/s32-17/acceptance_wall_v6_latest.json",
    "policy_drift": "docs/evidence/s32-18/policy_drift_guard_v2_latest.json",
    "reliability": "docs/evidence/s32-19/reliability_soak_v3_latest.json",
    "trend": "docs/evidence/s32-20/evidence_trend_index_v7_latest.json",
    "regression": "docs/evidence/s32-26/regression_safety_v3_latest.json",
}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _infer_status(doc: Dict[str, Any]) -> str:
    if not doc:
        return "MISSING"
    status = str(doc.get("status", "")).upper().strip()
    if status in {"PASS", "WARN", "ERROR"}:
        return "FAIL" if status == "ERROR" else status
    summary = dict(doc.get("summary", {}))
    s2 = str(summary.get("status", "")).upper().strip()
    if s2 in {"PASS", "WARN", "ERROR"}:
        return "FAIL" if s2 == "ERROR" else s2
    readiness = str(summary.get("readiness", "")).upper().strip()
    if readiness == "READY":
        return "PASS"
    if readiness == "CONDITIONAL_READY":
        return "WARN"
    if readiness == "BLOCKED":
        return "FAIL"
    return "MISSING"


def decide_readiness(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    missing = [r["id"] for r in rows if r["status"] == "MISSING"]
    fail = [r["id"] for r in rows if r["status"] == "FAIL"]
    warn = [r["id"] for r in rows if r["status"] == "WARN"]

    if missing or fail:
        return {
            "readiness": "BLOCKED",
            "reason": "MISSING_OR_FAIL",
            "missing": missing,
            "fail": fail,
            "warn": warn,
        }
    if warn:
        return {
            "readiness": "CONDITIONAL_READY",
            "reason": "WARN_PRESENT",
            "missing": [],
            "fail": [],
            "warn": warn,
        }
    return {
        "readiness": "READY",
        "reason": "ALL_PASS",
        "missing": [],
        "fail": [],
        "warn": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-27")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for key, rel in INPUTS.items():
        doc = _read_json((repo_root / rel).resolve())
        rows.append(
            {
                "id": key,
                "path": rel,
                "status": _infer_status(doc),
                "available": bool(doc),
            }
        )

    decision = decide_readiness(rows)
    payload = {
        "schema": "S32_RELEASE_READINESS_V2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputs": rows,
        "summary": decision,
    }

    (out_dir / "release_readiness_v2_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "release_readiness_v2_latest.md").write_text(
        "# S32-27 Release Readiness v2\n\n"
        f"- readiness: `{decision['readiness']}`\n"
        f"- reason: `{decision['reason']}`\n"
        f"- missing: `{','.join(decision['missing']) or '-'}`\n"
        f"- fail: `{','.join(decision['fail']) or '-'}`\n"
        f"- warn: `{','.join(decision['warn']) or '-'}`\n",
        encoding="utf-8",
    )

    print(
        "OK: s32_release_readiness_v2 readiness={readiness} reason={reason}".format(
            readiness=decision["readiness"],
            reason=decision["reason"],
        )
    )
    return 0 if decision["readiness"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
