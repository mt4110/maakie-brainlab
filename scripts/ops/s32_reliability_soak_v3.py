#!/usr/bin/env python3
"""
S32-19: reliability soak v3 (non-fixture + shard-oriented).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
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


def _run_once(repo_root: Path, cases_path: Path, run_out: Path) -> Dict[str, Any]:
    cmd = [
        "python3",
        "scripts/il_thread_runner_v2_orchestrator.py",
        "--cases",
        str(cases_path),
        "--mode",
        "validate-only",
        "--out",
        str(run_out),
        "--shard-count",
        "2",
    ]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + (proc.stderr or "")
    orch = _read_json(run_out / "summary.orchestrator.json")
    merged = dict(orch.get("merged_summary", {})) if orch else {}

    timeout_count = 0
    cases_rows = _read_jsonl(run_out / "merged" / "cases.jsonl")
    for row in cases_rows:
        timeout_count += sum(1 for code in row.get("entry_error_codes", []) if str(code) == "E_TIMEOUT")
    total_cases = int(merged.get("total_cases", 0))
    retry_total = int(merged.get("retry_attempts_total", merged.get("retries_used_count", 0)))
    lock_conflict = "E_ARTIFACT_LOCK" in output
    return {
        "returncode": proc.returncode,
        "total_cases": total_cases,
        "retry_attempts_total": retry_total,
        "timeout_count": timeout_count,
        "lock_conflict": lock_conflict,
        "ok": proc.returncode == 0,
        "output_tail": output[-800:],
    }


def _evaluate_status(*, total_runs: int, run_success_rate: float, timeout_rate: float, lock_conflict_rate: float) -> Dict[str, str]:
    if total_runs < 2:
        return {"status": "WARN", "reason_code": "INSUFFICIENT_SAMPLE"}
    if run_success_rate < 0.8:
        return {"status": "ERROR", "reason_code": "RUN_SUCCESS_RATE_LOW"}
    if timeout_rate > 0.1:
        return {"status": "WARN", "reason_code": "TIMEOUT_RATE_HIGH"}
    if lock_conflict_rate > 0.0:
        return {"status": "WARN", "reason_code": "LOCK_CONFLICT_DETECTED"}
    return {"status": "PASS", "reason_code": "STABLE"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-19")
    parser.add_argument("--cases", default="tests/fixtures/il_thread_runner/cases_smoke.jsonl")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cases_path = Path(args.cases).expanduser()
    if not cases_path.is_absolute():
        cases_path = (repo_root / cases_path).resolve()

    runs = max(1, int(args.runs))
    rows: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for i in range(1, runs + 1):
            row = _run_once(repo_root, cases_path, base / f"run_{i:02d}")
            row["run"] = i
            rows.append(row)

    success_runs = sum(1 for r in rows if bool(r.get("ok", False)))
    lock_conflicts = sum(1 for r in rows if bool(r.get("lock_conflict", False)))
    timeout_total = sum(int(r.get("timeout_count", 0)) for r in rows)
    total_cases = sum(int(r.get("total_cases", 0)) for r in rows)
    retry_total = sum(int(r.get("retry_attempts_total", 0)) for r in rows)

    run_success_rate = success_runs / runs
    timeout_rate = (timeout_total / total_cases) if total_cases > 0 else 0.0
    retry_rate = (retry_total / total_cases) if total_cases > 0 else 0.0
    lock_conflict_rate = lock_conflicts / runs
    verdict = _evaluate_status(
        total_runs=runs,
        run_success_rate=run_success_rate,
        timeout_rate=timeout_rate,
        lock_conflict_rate=lock_conflict_rate,
    )

    history_path = out_dir / "reliability_soak_history_v3.json"
    history: List[Dict[str, Any]] = []
    if history_path.exists():
        try:
            old = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(old, list):
                history = old
        except Exception:
            history = []

    trend_degraded = False
    if history:
        prev = history[-1]
        prev_rate = float(prev.get("run_success_rate", 0.0))
        if run_success_rate + 0.1 < prev_rate:
            trend_degraded = True
            if verdict["status"] == "PASS":
                verdict = {"status": "WARN", "reason_code": "SUCCESS_RATE_DEGRADED"}

    payload = {
        "schema": "S32_RELIABILITY_SOAK_V3",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": verdict["status"],
        "reason_code": verdict["reason_code"],
        "metrics": {
            "total_runs": runs,
            "run_success_rate": run_success_rate,
            "retry_rate": retry_rate,
            "timeout_rate": timeout_rate,
            "lock_conflict_rate": lock_conflict_rate,
            "trend_degraded": trend_degraded,
        },
        "runs": rows,
    }

    history.append(
        {
            "captured_at_utc": payload["captured_at_utc"],
            "status": payload["status"],
            "reason_code": payload["reason_code"],
            "run_success_rate": run_success_rate,
            "retry_rate": retry_rate,
            "timeout_rate": timeout_rate,
            "lock_conflict_rate": lock_conflict_rate,
        }
    )
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (out_dir / "reliability_soak_v3_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "reliability_soak_v3_latest.md").write_text(
        "# S32-19 Reliability Soak v3\n\n"
        f"- status: `{payload['status']}`\n"
        f"- reason_code: `{payload['reason_code']}`\n"
        f"- total_runs: `{runs}`\n"
        f"- run_success_rate: `{run_success_rate:.4f}`\n"
        f"- retry_rate: `{retry_rate:.4f}`\n"
        f"- timeout_rate: `{timeout_rate:.4f}`\n"
        f"- lock_conflict_rate: `{lock_conflict_rate:.4f}`\n",
        encoding="utf-8",
    )

    print(
        "OK: s32_reliability_soak_v3 status={status} runs={runs} success_rate={rate:.4f}".format(
            status=payload["status"],
            runs=runs,
            rate=run_success_rate,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
