#!/usr/bin/env python3
"""
S32-15: operator dashboard export for il_thread_runner_v2 artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
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


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _percentile95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = max(0, math.ceil(len(sorted_values) * 0.95) - 1)
    return float(sorted_values[idx])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="il_thread_runner_v2 output directory")
    parser.add_argument("--out-dir", default="docs/evidence/s32-15")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        run_dir = (repo_root / run_dir).resolve()
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (repo_root / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = _read_json(run_dir / "summary.json")
    cases = _read_jsonl(run_dir / "cases.jsonl")
    reasons: List[str] = []

    total_cases = int(summary.get("total_cases", len(cases)))
    mode = str(summary.get("mode", "validate-only"))
    compile_ok = int(summary.get("compile_ok_count", 0))
    entry_ok = int(summary.get("entry_ok_count", 0))
    retries_used = int(summary.get("retries_used_count", 0))

    success_numerator = compile_ok if mode == "validate-only" else entry_ok
    success_rate = (success_numerator / total_cases) if total_cases > 0 else 0.0
    retry_rate = (retries_used / total_cases) if total_cases > 0 else 0.0

    compile_latencies: List[float] = []
    for row in cases:
        artifacts = dict(row.get("artifacts", {}))
        rel = str(artifacts.get("compile_report", "")).strip()
        if not rel:
            continue
        report = _read_json(run_dir / rel)
        latency = report.get("compile_latency_ms")
        try:
            if latency is not None:
                compile_latencies.append(float(latency))
        except Exception:
            continue

    p95_latency_ms: float | None = None
    throughput_cases_per_sec: float | None = None
    if compile_latencies:
        p95_latency_ms = _percentile95(compile_latencies)
        total_latency_ms = sum(compile_latencies)
        throughput_cases_per_sec = (len(compile_latencies) / max(1.0, total_latency_ms / 1000.0))
    else:
        reasons.append("compile_latency_missing")

    if not summary:
        reasons.append("summary_missing_or_invalid")
    if not cases:
        reasons.append("cases_missing_or_invalid")

    payload = {
        "schema": "S32_OPERATOR_DASHBOARD_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PASS" if not reasons else "WARN",
        "run_dir": str(run_dir),
        "metrics": {
            "throughput_cases_per_sec": throughput_cases_per_sec,
            "success_rate": success_rate,
            "skip_breakdown": {
                "compile_skip_count": int(summary.get("compile_skip_count", 0)),
                "entry_skip_count": int(summary.get("entry_skip_count", 0)),
            },
            "retry_rate": retry_rate,
            "p95_latency_ms": p95_latency_ms,
        },
        "counts": {
            "total_cases": total_cases,
            "success_numerator": success_numerator,
            "retries_used_count": retries_used,
            "latency_sample_count": len(compile_latencies),
        },
        "reasons": reasons,
    }

    (out_dir / "operator_dashboard_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "operator_dashboard_latest.md").write_text(
        "# S32-15 Operator Dashboard\n\n"
        f"- status: `{payload['status']}`\n"
        f"- total_cases: `{total_cases}`\n"
        f"- success_rate: `{success_rate:.4f}`\n"
        f"- retry_rate: `{retry_rate:.4f}`\n"
        f"- p95_latency_ms: `{p95_latency_ms if p95_latency_ms is not None else 'NA'}`\n"
        f"- throughput_cases_per_sec: `{throughput_cases_per_sec if throughput_cases_per_sec is not None else 'NA'}`\n",
        encoding="utf-8",
    )

    print(
        "OK: s32_operator_dashboard_export status={status} total={total} success_rate={sr:.4f}".format(
            status=payload["status"],
            total=total_cases,
            sr=success_rate,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
