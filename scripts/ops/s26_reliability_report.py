#!/usr/bin/env python3
"""
S26-07 reliability report.

Goal:
- Summarize provider canary reliability with clear PASS/WARN/FAIL taxonomy.
- Keep SKIP-based runs visible without forcing hard failure.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s26-07"
DEFAULT_CANARY = "docs/evidence/s26-01/provider_canary_latest.json"
DEFAULT_ORCH = "docs/evidence/s26-04/orchestration_core_latest.json"

REASON_CANARY_MISSING = "CANARY_MISSING"
REASON_ORCHESTRATION_FAILED = "ORCHESTRATION_FAILED"
REASON_ORCHESTRATION_MISSING = "ORCHESTRATION_MISSING"
REASON_CANARY_FAILED = "CANARY_FAILED"
REASON_NO_RUNNABLE_CASES = "NO_RUNNABLE_CASES"
REASON_SUCCESS_RATE_LOW = "SUCCESS_RATE_LOW"
REASON_FAILED_CASES_EXCEEDED = "FAILED_CASES_EXCEEDED"


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    text = rel.as_posix()
    if ".." in Path(text).parts:
        return ""
    return text


def read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def count_reason_codes(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in cases:
        code = str(row.get("reason_code") or "")
        if not code:
            continue
        counts[code] = int(counts.get(code, 0)) + 1
    return dict(sorted(counts.items(), key=lambda x: x[0]))


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    metrics = payload["metrics"]
    lines: List[str] = []
    lines.append("# S26-07 Reliability Report (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- runnable_cases: `{metrics.get('runnable_cases', 0)}`")
    lines.append(f"- passed_failed_skipped: `{metrics.get('passed_cases', 0)}/{metrics.get('failed_cases', 0)}/{metrics.get('skipped_cases', 0)}`")
    lines.append(f"- success_rate: `{metrics.get('success_rate')}`")
    lines.append(f"- avg_attempts_per_runnable_case: `{metrics.get('avg_attempts_per_runnable_case')}`")
    lines.append("")
    lines.append("## Reason Counts")
    lines.append("")
    if payload.get("reason_counts"):
        for key, value in dict(payload.get("reason_counts", {})).items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-07 Reliability Report")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- runnable_cases: {metrics.get('runnable_cases', 0)}")
    lines.append(f"- success_rate: {metrics.get('success_rate')}")
    lines.append(f"- reason_counts: {payload.get('reason_counts', {}) or 'none'}")
    lines.append(f"- artifact: docs/evidence/s26-07/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure_artifacts(
    *,
    repo_root: Path,
    out_dir: Path,
    canary_path: Path,
    orch_path: Path,
    reason_code: str,
) -> None:
    payload: Dict[str, Any] = {
        "schema_version": "s26-reliability-report-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "canary_json": to_repo_rel(repo_root, canary_path),
            "orchestration_json": to_repo_rel(repo_root, orch_path),
            "min_success_rate": None,
            "max_failed_cases": None,
        },
        "metrics": {
            "passed_cases": 0,
            "failed_cases": 0,
            "skipped_cases": 0,
            "runnable_cases": 0,
            "success_rate": None,
            "avg_attempts_per_runnable_case": None,
        },
        "reason_counts": {},
        "summary": {
            "status": "FAIL",
            "reason_code": reason_code,
        },
        "artifact_names": {
            "json": "reliability_report_latest.json",
            "md": "reliability_report_latest.md",
        },
    }
    out_json = out_dir / "reliability_report_latest.json"
    out_md = out_dir / "reliability_report_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--canary-json", default=DEFAULT_CANARY)
    parser.add_argument("--orchestration-json", default=DEFAULT_ORCH)
    parser.add_argument("--min-success-rate", type=float, default=0.8)
    parser.add_argument("--max-failed-cases", type=int, default=0)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-reliability-report", obs_root=args.obs_root)

    canary_path = (repo_root / args.canary_json).resolve()
    orch_path = (repo_root / args.orchestration_json).resolve()
    canary = read_json_if_exists(canary_path)
    orchestration = read_json_if_exists(orch_path)

    if not canary:
        emit("ERROR", f"canary evidence missing path={canary_path}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            canary_path=canary_path,
            orch_path=orch_path,
            reason_code=REASON_CANARY_MISSING,
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CANARY_MISSING})
        return 1
    if not orchestration:
        emit("ERROR", f"orchestration evidence missing path={orch_path}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            canary_path=canary_path,
            orch_path=orch_path,
            reason_code=REASON_ORCHESTRATION_MISSING,
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_ORCHESTRATION_MISSING})
        return 1

    canary_summary = dict(canary.get("summary", {}))
    canary_cases = list(canary.get("cases", [])) if isinstance(canary.get("cases"), list) else []
    passed_cases = to_int(canary_summary.get("passed_cases", 0), 0)
    failed_cases = to_int(canary_summary.get("failed_cases", 0), 0)
    skipped_cases = to_int(canary_summary.get("skipped_cases", 0), 0)
    runnable_cases = max(0, passed_cases + failed_cases)

    total_attempts = 0
    for row in canary_cases:
        attempts = row.get("attempts")
        if isinstance(attempts, list):
            total_attempts += len(attempts)

    success_rate = None if runnable_cases == 0 else round(passed_cases / float(runnable_cases), 4)
    avg_attempts = None if runnable_cases == 0 else round(total_attempts / float(runnable_cases), 3)
    reason_counts = count_reason_codes(canary_cases)

    status = "PASS"
    reason_code = ""

    orch_status = str(dict(orchestration.get("summary", {})).get("status") or "")
    if orch_status == "FAIL":
        status = "FAIL"
        reason_code = REASON_ORCHESTRATION_FAILED
    elif str(canary_summary.get("status") or "") == "FAIL":
        status = "FAIL"
        reason_code = REASON_CANARY_FAILED
    elif runnable_cases == 0:
        status = "WARN"
        reason_code = REASON_NO_RUNNABLE_CASES
    elif success_rate is not None and success_rate < float(args.min_success_rate):
        status = "FAIL"
        reason_code = REASON_SUCCESS_RATE_LOW
    elif failed_cases > int(args.max_failed_cases):
        status = "FAIL"
        reason_code = REASON_FAILED_CASES_EXCEEDED

    emit("OK", f"canary_status={canary_summary.get('status')} orch_status={orch_status}", events)
    emit("OK", f"runnable={runnable_cases} pass/fail/skip={passed_cases}/{failed_cases}/{skipped_cases}", events)
    if status == "FAIL":
        emit("ERROR", f"reliability status=FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"reliability status=WARN reason={reason_code}", events)
    else:
        emit("OK", "reliability status=PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s26-reliability-report-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "canary_json": to_repo_rel(repo_root, canary_path),
            "orchestration_json": to_repo_rel(repo_root, orch_path),
            "min_success_rate": float(args.min_success_rate),
            "max_failed_cases": int(args.max_failed_cases),
        },
        "metrics": {
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "skipped_cases": skipped_cases,
            "runnable_cases": runnable_cases,
            "success_rate": success_rate,
            "avg_attempts_per_runnable_case": avg_attempts,
        },
        "reason_counts": reason_counts,
        "summary": {
            "status": status,
            "reason_code": reason_code,
        },
        "artifact_names": {
            "json": "reliability_report_latest.json",
            "md": "reliability_report_latest.md",
        },
    }

    out_json = out_dir / "reliability_report_latest.json"
    out_md = out_dir / "reliability_report_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
