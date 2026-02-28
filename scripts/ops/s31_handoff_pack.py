#!/usr/bin/env python3
"""
S31-30: generate S32 handoff pack.
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
    parser.add_argument("--out-dir", default="docs/evidence/s31-30")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    closeout = _read_json((repo_root / "docs/evidence/s31-29/closeout_latest.json").resolve())
    closeout_status = str(closeout.get("status", "WARN"))

    payload = {
        "schema": "S31_HANDOFF_PACK_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "s31_closeout_status": closeout_status,
        "s32_start_conditions": {
            "closeout_available": bool(closeout),
            "verify_il_green_required": True,
            "thread_runner_suite_green_required": True,
        },
        "priority_backlog": [
            {"id": "S32-01", "title": "RAG quality uplift for non-fixture corpora"},
            {"id": "S32-02", "title": "Compile prompt profile auto-selection"},
            {"id": "S32-03", "title": "Runner distributed shard orchestrator"},
        ],
    }

    (out_dir / "handoff_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "handoff_latest.md").write_text(
        "# S31 -> S32 Handoff\n\n"
        f"- s31_closeout_status: `{closeout_status}`\n"
        "- start_conditions: closeout available + verify-il green + suite green\n",
        encoding="utf-8",
    )

    print(f"OK: s31_handoff_pack status={closeout_status}")
    return 0 if closeout_status in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
