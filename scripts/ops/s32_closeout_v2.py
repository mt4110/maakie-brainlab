#!/usr/bin/env python3
"""
S32-28: closeout generator v2.
"""

from __future__ import annotations

import argparse
import json
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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-28")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    s31_closeout = _read_json((repo_root / "docs/evidence/s31-29/closeout_latest.json").resolve())
    s32_readiness = _read_json((repo_root / "docs/evidence/s32-27/release_readiness_v2_latest.json").resolve())
    s32_latency = _read_json((repo_root / "docs/evidence/s32-16/latency_slo_guard_latest.json").resolve())
    s32_dashboard = _read_json((repo_root / "docs/evidence/s32-15/operator_dashboard_latest.json").resolve())
    s32_reliability = _read_json((repo_root / "docs/evidence/s32-19/reliability_soak_v3_latest.json").resolve())

    readiness = str(dict(s32_readiness.get("summary", {})).get("readiness", "BLOCKED"))
    status = "PASS" if readiness == "READY" else "WARN"

    before_quality = _to_float(dict(s31_closeout.get("summary", {})).get("checks_pass", 0))
    after_quality = 0.0
    if s32_readiness:
        rows = list(s32_readiness.get("inputs", []))
        after_quality = float(sum(1 for r in rows if str(r.get("status")) == "PASS"))

    before_latency = _to_optional_float(
        dict(dict(s31_closeout.get("before_after", {})).get("latency", {})).get("after_p95_latency_ms")
    )
    if before_latency is None:
        before_latency = _to_optional_float(dict(s31_closeout.get("summary", {})).get("p95_latency_ms"))
    after_latency = dict(s32_latency.get("summary", {})).get("p95_latency_ms")

    retry_rate = _to_float(dict(s32_dashboard.get("metrics", {})).get("retry_rate", 0.0))
    run_success_rate = _to_float(dict(s32_reliability.get("metrics", {})).get("run_success_rate", 0.0))

    unresolved_risks: List[str] = []
    if readiness != "READY":
        unresolved_risks.append(f"release_readiness={readiness}")
    warn_rows = list(dict(s32_readiness.get("summary", {})).get("warn", []))
    for row in warn_rows:
        unresolved_risks.append(f"warn_input:{row}")
    for row in list(dict(s32_readiness.get("summary", {})).get("missing", [])):
        unresolved_risks.append(f"missing_input:{row}")
    if retry_rate > 0.1:
        unresolved_risks.append(f"retry_rate_high:{retry_rate:.4f}")
    if run_success_rate < 1.0:
        unresolved_risks.append(f"run_success_rate_below_one:{run_success_rate:.4f}")

    payload = {
        "schema": "S32_CLOSEOUT_V2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "readiness": readiness,
        "before_after": {
            "quality": {"before_pass_count": before_quality, "after_pass_count": after_quality},
            "latency": {"before_p95_latency_ms": before_latency, "after_p95_latency_ms": after_latency},
            "operability": {"retry_rate": retry_rate, "run_success_rate": run_success_rate},
        },
        "unresolved_risks": unresolved_risks,
    }

    (out_dir / "closeout_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "closeout_latest.md").write_text(
        "# S32-28 Closeout v2\n\n"
        f"- status: `{status}`\n"
        f"- readiness: `{readiness}`\n"
        f"- unresolved_risks: `{len(unresolved_risks)}`\n",
        encoding="utf-8",
    )

    print(f"OK: s32_closeout_v2 status={status} readiness={readiness} risks={len(unresolved_risks)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
