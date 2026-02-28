#!/usr/bin/env python3
"""
S32-16: latency budget/SLO guard.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


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


def _pct(values: List[float], ratio: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = max(0, math.ceil(len(sorted_values) * ratio) - 1)
    return float(sorted_values[idx])


def collect_compile_latencies_ms(run_dir: Path) -> Tuple[List[float], List[Dict[str, Any]]]:
    rows = _read_jsonl(run_dir / "cases.jsonl")
    values: List[float] = []
    details: List[Dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("id", ""))
        artifacts = dict(row.get("artifacts", {}))
        rel = str(artifacts.get("compile_report", "")).strip()
        if not rel:
            continue
        report = _read_json(run_dir / rel)
        latency = report.get("compile_latency_ms")
        try:
            ms = float(latency)
        except Exception:
            continue
        values.append(ms)
        details.append({"id": case_id, "compile_latency_ms": ms})
    return values, details


def evaluate_latency_guard(
    latencies_ms: List[float],
    *,
    budget_p50_ms: float,
    budget_p95_ms: float,
    timeout_ms: float,
    min_samples: int,
) -> Dict[str, Any]:
    sample_count = len(latencies_ms)
    if sample_count < min_samples:
        return {
            "status": "WARN",
            "reason_code": "INSUFFICIENT_SAMPLE",
            "sample_count": sample_count,
            "p50_latency_ms": _pct(latencies_ms, 0.50) if latencies_ms else None,
            "p95_latency_ms": _pct(latencies_ms, 0.95) if latencies_ms else None,
            "breach_count": 0,
            "worst_latency_ms": max(latencies_ms) if latencies_ms else None,
            "recommended_actions": ["increase sample size and rerun latency guard"],
        }

    p50 = _pct(latencies_ms, 0.50)
    p95 = _pct(latencies_ms, 0.95)
    worst = max(latencies_ms)
    timeout_breach = sum(1 for x in latencies_ms if x > timeout_ms)
    budget_breach = sum(1 for x in latencies_ms if x > budget_p95_ms)

    status = "PASS"
    reason = "WITHIN_BUDGET"
    actions: List[str] = []
    if timeout_breach > 0:
        status = "ERROR"
        reason = "TIMEOUT_BREACH"
        actions.append("investigate outlier cases and enforce tighter timeout controls")
    elif p95 > budget_p95_ms or p50 > budget_p50_ms:
        status = "WARN"
        reason = "BUDGET_BREACH"
        actions.append("optimize compile path or relax workload complexity for hot cases")
    else:
        actions.append("keep monitoring latency trend for regressions")

    return {
        "status": status,
        "reason_code": reason,
        "sample_count": sample_count,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "breach_count": timeout_breach if timeout_breach > 0 else budget_breach,
        "worst_latency_ms": worst,
        "recommended_actions": actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out-dir", default="docs/evidence/s32-16")
    parser.add_argument("--budget-p50-ms", type=float, default=80.0)
    parser.add_argument("--budget-p95-ms", type=float, default=200.0)
    parser.add_argument("--timeout-ms", type=float, default=1000.0)
    parser.add_argument("--min-samples", type=int, default=3)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        run_dir = (repo_root / run_dir).resolve()
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (repo_root / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    latencies, details = collect_compile_latencies_ms(run_dir)
    result = evaluate_latency_guard(
        latencies,
        budget_p50_ms=float(args.budget_p50_ms),
        budget_p95_ms=float(args.budget_p95_ms),
        timeout_ms=float(args.timeout_ms),
        min_samples=max(1, int(args.min_samples)),
    )

    worst_case = None
    if details:
        worst_case = max(details, key=lambda x: float(x.get("compile_latency_ms", 0.0)))

    payload = {
        "schema": "S32_LATENCY_SLO_GUARD_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_dir": str(run_dir),
        "budgets": {
            "p50_ms": float(args.budget_p50_ms),
            "p95_ms": float(args.budget_p95_ms),
            "timeout_ms": float(args.timeout_ms),
            "min_samples": max(1, int(args.min_samples)),
        },
        "summary": result,
        "worst_case": worst_case,
    }

    (out_dir / "latency_slo_guard_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "latency_slo_guard_latest.md").write_text(
        "# S32-16 Latency SLO Guard\n\n"
        f"- status: `{result['status']}`\n"
        f"- reason_code: `{result['reason_code']}`\n"
        f"- sample_count: `{result['sample_count']}`\n"
        f"- p50_latency_ms: `{result['p50_latency_ms']}`\n"
        f"- p95_latency_ms: `{result['p95_latency_ms']}`\n"
        f"- breach_count: `{result['breach_count']}`\n",
        encoding="utf-8",
    )

    print(
        "OK: s32_latency_slo_guard status={status} sample={sample} p95={p95}".format(
            status=result["status"],
            sample=result["sample_count"],
            p95=result["p95_latency_ms"],
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
