#!/usr/bin/env python3
"""
S31-10: compare compile bench summary against a baseline.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict


METRICS = (
    "expected_match_rate",
    "reproducible_rate",
    "fallback_rate",
    "objective_score",
)


def _read_json(path: Path) -> Dict[str, Any]:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--max-fallback-regression", type=float, default=0.02)
    parser.add_argument("--min-objective-improvement", type=float, default=-0.0001)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    baseline_path = Path(args.baseline).expanduser().resolve()
    candidate_path = Path(args.candidate).expanduser().resolve()
    baseline = _read_json(baseline_path)
    candidate = _read_json(candidate_path)

    if not baseline or not candidate:
        print("ERROR: failed to read baseline/candidate summaries")
        return 1

    diff: Dict[str, Any] = {
        "schema": "IL_COMPILE_BENCH_DIFF_v1",
        "baseline": str(baseline_path),
        "candidate": str(candidate_path),
        "metrics": {},
        "status": "OK",
        "checks": [],
    }

    for metric in METRICS:
        b = _to_float(baseline.get(metric, 0.0))
        c = _to_float(candidate.get(metric, 0.0))
        diff["metrics"][metric] = {
            "baseline": b,
            "candidate": c,
            "delta": c - b,
        }

    fallback_delta = float(diff["metrics"]["fallback_rate"]["delta"])
    objective_delta = float(diff["metrics"]["objective_score"]["delta"])

    fallback_ok = fallback_delta <= float(args.max_fallback_regression)
    objective_ok = objective_delta >= float(args.min_objective_improvement)

    diff["checks"].append(
        {
            "name": "fallback_regression",
            "status": "OK" if fallback_ok else "ERROR",
            "target": f"delta <= {args.max_fallback_regression}",
            "observed": fallback_delta,
        }
    )
    diff["checks"].append(
        {
            "name": "objective_delta",
            "status": "OK" if objective_ok else "ERROR",
            "target": f"delta >= {args.min_objective_improvement}",
            "observed": objective_delta,
        }
    )

    if not (fallback_ok and objective_ok):
        diff["status"] = "ERROR"

    text = json.dumps(diff, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")

    print(f"OK: bench_diff status={diff['status']}")
    print(
        "OK: bench_diff_summary fallback_delta={:.6f} objective_delta={:.6f}".format(
            fallback_delta,
            objective_delta,
        )
    )

    return 0 if diff["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
