#!/usr/bin/env python3
"""
S29-06 reliability soak v3.

Goal:
- Evaluate long-run non-pass streaks and recovery signal readiness.
- Keep thresholds explicit for non-blocking operation monitoring.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s29-06"
DEFAULT_HISTORY = "docs/evidence/s27-01/provider_canary_history.json"
DEFAULT_RECOVERY = "docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json"

REASON_HISTORY_MISSING = "HISTORY_MISSING"
REASON_INSUFFICIENT_RUNS = "INSUFFICIENT_RUNS"
REASON_INSUFFICIENT_RUNS_ENV_GAP = "INSUFFICIENT_RUNS_ENV_GAP"
REASON_TARGET_RUNS_NOT_REACHED = "TARGET_RUNS_NOT_REACHED"
REASON_CONSECUTIVE_NONPASS = "CONSECUTIVE_NONPASS"
REASON_FAIL_RATE_HIGH = "FAIL_RATE_HIGH"
REASON_SKIP_RATE_HIGH = "SKIP_RATE_HIGH"
REASON_SKIP_RATE_HIGH_ENV_GAP = "SKIP_RATE_HIGH_ENV_GAP"
REASON_RECOVERY_SIGNAL_MISSING = "RECOVERY_SIGNAL_MISSING"


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


def parse_hour(value: str) -> int:
    text = str(value or "")
    if not text:
        return -1
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(dt.hour)
    except Exception:
        return -1


def longest_consecutive_status(runs: List[Dict[str, Any]], target_statuses: set[str]) -> int:
    best = 0
    cur = 0
    for row in runs:
        st = str(row.get("status") or "").upper()
        if st in target_statuses:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def reason_code_counts(runs: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in runs:
        reason = str(row.get("reason_code") or "").strip()
        if not reason:
            continue
        counts[reason] = int(counts.get(reason, 0)) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def env_gap_profile(runs: List[Dict[str, Any]]) -> Dict[str, float | int]:
    total_runs = len(runs)
    env_gap_runs = sum(1 for row in runs if str(row.get("reason_code") or "").upper() == "MISSING_PROVIDER_ENV")
    env_gap_ratio = 0.0 if total_runs <= 0 else round(env_gap_runs / float(total_runs), 4)
    return {
        "env_gap_runs": env_gap_runs,
        "env_gap_ratio": env_gap_ratio,
    }


def evaluate_reliability_status(
    *,
    history_present: bool,
    total_runs: int,
    min_runs: int,
    target_runs: int,
    max_consecutive_nonpass: int,
    max_consecutive_threshold: int,
    fail_rate: float,
    fail_rate_hard_threshold: float,
    skip_rate: float,
    skip_rate_warn_threshold: float,
    recovery_present: bool,
    dominant_reason_code: str,
    env_gap_ratio: float,
) -> tuple[str, str]:
    if not history_present:
        return "WARN", REASON_HISTORY_MISSING
    if total_runs < min_runs:
        if dominant_reason_code == "MISSING_PROVIDER_ENV":
            return "WARN", REASON_INSUFFICIENT_RUNS_ENV_GAP
        return "WARN", REASON_INSUFFICIENT_RUNS
    if max_consecutive_nonpass > max_consecutive_threshold:
        return "FAIL", REASON_CONSECUTIVE_NONPASS
    if fail_rate > fail_rate_hard_threshold:
        return "FAIL", REASON_FAIL_RATE_HIGH
    if skip_rate > skip_rate_warn_threshold:
        if env_gap_ratio >= 0.8:
            return "WARN", REASON_SKIP_RATE_HIGH_ENV_GAP
        return "WARN", REASON_SKIP_RATE_HIGH
    if not recovery_present:
        return "WARN", REASON_RECOVERY_SIGNAL_MISSING
    if total_runs < target_runs:
        return "WARN", REASON_TARGET_RUNS_NOT_REACHED
    return "PASS", ""


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    metrics = dict(payload.get("metrics", {}))
    lines: List[str] = []
    lines.append("# S29-06 Reliability Soak v3 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- total_runs: `{metrics.get('total_runs', 0)}`")
    lines.append(f"- skip_rate: `{metrics.get('skip_rate', 0.0)}`")
    lines.append(f"- fail_rate: `{metrics.get('fail_rate', 0.0)}`")
    lines.append(f"- max_consecutive_nonpass: `{metrics.get('max_consecutive_nonpass', 0)}`")
    lines.append(f"- recovery_status: `{metrics.get('recovery_status', '')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--history-json", default=DEFAULT_HISTORY)
    parser.add_argument("--recovery-json", default=DEFAULT_RECOVERY)
    parser.add_argument("--min-runs", type=int, default=6)
    parser.add_argument("--target-runs", type=int, default=24)
    parser.add_argument("--max-consecutive-nonpass", type=int, default=4)
    parser.add_argument("--fail-rate-hard-threshold", type=float, default=0.30)
    parser.add_argument("--skip-rate-warn-threshold", type=float, default=0.50)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s29-reliability-soak-v3", obs_root=args.obs_root)

    history_path = (repo_root / str(args.history_json)).resolve()
    recovery_path = (repo_root / str(args.recovery_json)).resolve()
    hist = read_json_if_exists(history_path)
    recovery = read_json_if_exists(recovery_path)
    runs = list(hist.get("runs", [])) if isinstance(hist.get("runs"), list) else []

    if not hist:
        emit("WARN", f"history missing path={history_path}", events)

    total_runs = len(runs)
    fail_runs = sum(1 for x in runs if str(x.get("status") or "").upper() == "FAIL")
    skip_runs = sum(1 for x in runs if str(x.get("status") or "").upper() == "SKIP")
    warn_runs = sum(1 for x in runs if str(x.get("status") or "").upper() == "WARN")
    fail_rate = 0.0 if total_runs == 0 else round(fail_runs / float(total_runs), 4)
    skip_rate = 0.0 if total_runs == 0 else round(skip_runs / float(total_runs), 4)
    max_consecutive_nonpass = longest_consecutive_status(runs, {"FAIL", "SKIP"})

    hour_bucket_counts: Dict[str, int] = {}
    for row in runs:
        hour = parse_hour(str(row.get("captured_at_utc") or ""))
        key = "unknown" if hour < 0 else f"{hour:02d}:00"
        hour_bucket_counts[key] = int(hour_bucket_counts.get(key, 0)) + 1

    recovery_status = str(dict(recovery.get("summary", {})).get("status") or "")
    reason_counts = reason_code_counts(runs)
    dominant_reason_code = next(iter(reason_counts.keys()), "")
    env_gap = env_gap_profile(runs)
    status, reason_code = evaluate_reliability_status(
        history_present=bool(hist),
        total_runs=total_runs,
        min_runs=int(args.min_runs),
        target_runs=max(int(args.target_runs), int(args.min_runs)),
        max_consecutive_nonpass=max_consecutive_nonpass,
        max_consecutive_threshold=int(args.max_consecutive_nonpass),
        fail_rate=fail_rate,
        fail_rate_hard_threshold=float(args.fail_rate_hard_threshold),
        skip_rate=skip_rate,
        skip_rate_warn_threshold=float(args.skip_rate_warn_threshold),
        recovery_present=bool(recovery),
        dominant_reason_code=dominant_reason_code,
        env_gap_ratio=float(env_gap.get("env_gap_ratio", 0.0)),
    )

    if reason_code in {REASON_INSUFFICIENT_RUNS, REASON_INSUFFICIENT_RUNS_ENV_GAP}:
        emit("WARN", f"insufficient runs total={total_runs} min={args.min_runs}", events)

    if status == "FAIL":
        emit("ERROR", f"soak v3 FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"soak v3 WARN reason={reason_code}", events)
    else:
        emit("OK", "soak v3 PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s29-reliability-soak-v3",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "history_json": to_repo_rel(repo_root, history_path),
            "recovery_json": to_repo_rel(repo_root, recovery_path),
            "min_runs": int(args.min_runs),
            "target_runs": max(int(args.target_runs), int(args.min_runs)),
            "max_consecutive_nonpass": int(args.max_consecutive_nonpass),
            "fail_rate_hard_threshold": float(args.fail_rate_hard_threshold),
            "skip_rate_warn_threshold": float(args.skip_rate_warn_threshold),
        },
        "metrics": {
            "total_runs": total_runs,
            "fail_runs": fail_runs,
            "skip_runs": skip_runs,
            "warn_runs": warn_runs,
            "fail_rate": fail_rate,
            "skip_rate": skip_rate,
            "max_consecutive_nonpass": max_consecutive_nonpass,
            "hour_bucket_counts": dict(sorted(hour_bucket_counts.items(), key=lambda x: x[0])),
            "recovery_status": recovery_status,
            "reason_code_counts": reason_counts,
            "env_gap_runs": int(env_gap.get("env_gap_runs", 0)),
            "env_gap_ratio": float(env_gap.get("env_gap_ratio", 0.0)),
            "remaining_runs_to_target": max(0, max(int(args.target_runs), int(args.min_runs)) - total_runs),
        },
        "summary": {"status": status, "reason_code": reason_code},
        "artifact_names": {"json": "reliability_soak_v3_latest.json", "md": "reliability_soak_v3_latest.md"},
    }

    out_json = out_dir / "reliability_soak_v3_latest.json"
    out_md = out_dir / "reliability_soak_v3_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "total_runs": total_runs})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
