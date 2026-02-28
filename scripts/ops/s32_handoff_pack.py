#!/usr/bin/env python3
"""
S32-29/30: S33 backlog seed pack + handoff pack.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_pending_ops(task_text: str) -> List[str]:
    rows: List[str] = []
    for line in task_text.splitlines():
        m = re.match(r"^\s*-\s\[\s\]\s(.+?)\s*$", line)
        if m:
            rows.append(m.group(1))
    return rows


def _risk_priority(text: str) -> int:
    t = str(text).lower()
    if "blocked" in t or "missing" in t:
        return 95
    if "warn" in t or "high" in t:
        return 85
    return 75


def generate_backlog_seed(closeout: Dict[str, Any], trend: Dict[str, Any], pending_ops: List[str]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    unresolved = list(closeout.get("unresolved_risks", []))
    for risk in unresolved:
        text = str(risk)
        candidates.append(
            {
                "title": f"Resolve closeout risk: {text}",
                "rationale": "Derived from S32 closeout unresolved risk.",
                "dependency": "S32-28 closeout",
                "priority": _risk_priority(text),
            }
        )

    for row in list(trend.get("rows", [])):
        if not isinstance(row, dict):
            continue
        if str(row.get("status")) == "PASS":
            continue
        phase = str(row.get("phase", "unknown"))
        candidates.append(
            {
                "title": f"Stabilize evidence phase {phase}",
                "rationale": "Phase is WARN in evidence trend index v7.",
                "dependency": str(row.get("path", "")),
                "priority": 82,
            }
        )

    for op in pending_ops:
        candidates.append(
            {
                "title": f"Carry over pending op: {op}",
                "rationale": "Open item from S32 task checklist.",
                "dependency": "docs/ops/S32-01-S32-30-THREAD-V1_TASK.md",
                "priority": 70,
            }
        )

    ranked = sorted(
        candidates,
        key=lambda x: (-int(x.get("priority", 0)), str(x.get("title", "")), str(x.get("dependency", ""))),
    )

    out: List[Dict[str, Any]] = []
    for i, row in enumerate(ranked[:10], 1):
        out.append(
            {
                "id": f"S33-BK-{i:03d}",
                "priority": int(row["priority"]),
                "title": row["title"],
                "rationale": row["rationale"],
                "dependency": row["dependency"],
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir-29", default="docs/evidence/s32-29")
    parser.add_argument("--out-dir-30", default="docs/evidence/s32-30")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out29 = (repo_root / args.out_dir_29).resolve()
    out30 = (repo_root / args.out_dir_30).resolve()
    out29.mkdir(parents=True, exist_ok=True)
    out30.mkdir(parents=True, exist_ok=True)

    closeout = _read_json((repo_root / "docs/evidence/s32-28/closeout_latest.json").resolve())
    trend = _read_json((repo_root / "docs/evidence/s32-20/evidence_trend_index_v7_latest.json").resolve())
    task_text = _read_text((repo_root / "docs/ops/S32-01-S32-30-THREAD-V1_TASK.md").resolve())
    pending_ops = _extract_pending_ops(task_text)

    backlog = generate_backlog_seed(closeout, trend, pending_ops)
    backlog_payload = {
        "schema": "S32_S33_BACKLOG_SEED_PACK_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "closeout_available": bool(closeout),
        "trend_available": bool(trend),
        "pending_ops_count": len(pending_ops),
        "items": backlog,
    }
    (out29 / "s33_backlog_seed_latest.json").write_text(
        json.dumps(backlog_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out29 / "s33_backlog_seed_latest.md").write_text(
        "# S32-29 S33 Backlog Seed Pack\n\n"
        f"- items: `{len(backlog)}`\n"
        f"- closeout_available: `{bool(closeout)}`\n"
        f"- trend_available: `{bool(trend)}`\n",
        encoding="utf-8",
    )

    closeout_status = str(closeout.get("status", "WARN"))
    handoff_payload = {
        "schema": "S32_S33_HANDOFF_PACK_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "s32_closeout_status": closeout_status,
        "s33_start_conditions": {
            "closeout_available": bool(closeout),
            "verify_il_green_required": True,
            "suite_green_required": True,
            "ops_now_snapshot_required": True,
        },
        "priority_backlog": backlog[:5],
        "backlog_artifact": "docs/evidence/s32-29/s33_backlog_seed_latest.json",
        "required_commands": ["make ops-now", "make verify-il"],
    }
    (out30 / "handoff_latest.json").write_text(
        json.dumps(handoff_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out30 / "handoff_latest.md").write_text(
        "# S32-30 S33 Handoff Pack\n\n"
        f"- s32_closeout_status: `{closeout_status}`\n"
        "- start_conditions: closeout available + verify-il green + suite green + ops-now snapshot\n"
        "- backlog: `docs/evidence/s32-29/s33_backlog_seed_latest.json`\n",
        encoding="utf-8",
    )

    print(
        "OK: s32_handoff_pack closeout_status={status} backlog_items={count}".format(
            status=closeout_status,
            count=len(backlog),
        )
    )
    return 0 if bool(closeout) else 1


if __name__ == "__main__":
    raise SystemExit(main())
