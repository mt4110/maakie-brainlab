#!/usr/bin/env python3
"""
S27-04 incident triage pack.

Goal:
- Aggregate minimal diagnostics for fast initial triage.
- Keep rollback path visible with top reason-code hints.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s27-04"
DEFAULT_CANARY_OPS = "docs/evidence/s27-01/provider_canary_ops_latest.json"
DEFAULT_CANARY_BASE = "docs/evidence/s27-01/provider_canary_latest.json"
DEFAULT_MEDIUM_V2 = "docs/evidence/s27-02/medium_eval_wall_v2_latest.json"
DEFAULT_SCHEDULE = "docs/evidence/s27-03/release_readiness_schedule_latest.json"

REASON_ALL_INPUTS_MISSING = "ALL_INPUTS_MISSING"
REASON_PARTIAL_INPUTS_MISSING = "PARTIAL_INPUTS_MISSING"
REASON_TRIAGE_ALERT = "TRIAGE_ALERT"


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


def count_reason(reason_counts: Dict[str, int], code: str) -> None:
    if not code:
        return
    reason_counts[code] = int(reason_counts.get(code, 0)) + 1


def top_reason_codes(reason_counts: Dict[str, int], limit: int = 5) -> List[Tuple[str, int]]:
    rows = sorted(reason_counts.items(), key=lambda x: (-x[1], x[0]))
    return rows[: max(1, int(limit))]


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    lines: List[str] = []
    lines.append("# S27-04 Incident Triage Pack (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- missing_inputs: `{summary.get('missing_inputs', 0)}`")
    lines.append(f"- alerts: `{summary.get('alerts', 0)}`")
    lines.append("")
    lines.append("## Top Reasons")
    lines.append("")
    for row in list(payload.get("top_reasons", [])):
        lines.append(f"- {row.get('reason_code')}: `{row.get('count')}`")
    if not payload.get("top_reasons"):
        lines.append("- none")
    lines.append("")
    lines.append("## Rollback")
    lines.append("")
    lines.append(f"- command: `{payload.get('rollback_command', '')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S27-04 Incident Triage Pack")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- top_reasons: {payload.get('top_reasons', [])}")
    lines.append(f"- rollback: {payload.get('rollback_command', '')}")
    lines.append(f"- artifact: docs/evidence/s27-04/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--canary-ops-json", default=DEFAULT_CANARY_OPS)
    parser.add_argument("--canary-base-json", default=DEFAULT_CANARY_BASE)
    parser.add_argument("--medium-json", default=DEFAULT_MEDIUM_V2)
    parser.add_argument("--schedule-json", default=DEFAULT_SCHEDULE)
    parser.add_argument("--recent-limit", type=int, default=5)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s27-incident-triage-pack", obs_root=args.obs_root)

    canary_ops_path = (repo_root / args.canary_ops_json).resolve()
    canary_base_path = (repo_root / args.canary_base_json).resolve()
    medium_path = (repo_root / args.medium_json).resolve()
    schedule_path = (repo_root / args.schedule_json).resolve()

    canary_ops = read_json_if_exists(canary_ops_path)
    canary_base = read_json_if_exists(canary_base_path)
    medium = read_json_if_exists(medium_path)
    schedule = read_json_if_exists(schedule_path)

    inputs = {
        "canary_ops_json": to_repo_rel(repo_root, canary_ops_path),
        "canary_base_json": to_repo_rel(repo_root, canary_base_path),
        "medium_json": to_repo_rel(repo_root, medium_path),
        "schedule_json": to_repo_rel(repo_root, schedule_path),
    }
    missing_inputs = [k for k, v in [("canary_ops_json", canary_ops), ("canary_base_json", canary_base), ("medium_json", medium), ("schedule_json", schedule)] if not v]
    for name in missing_inputs:
        emit("WARN", f"missing input={name}", events)

    reason_counts: Dict[str, int] = {}
    count_reason(reason_counts, str(dict(canary_ops.get("summary", {})).get("reason_code") or ""))
    count_reason(reason_counts, str(dict(canary_base.get("summary", {})).get("reason_code") or ""))
    count_reason(reason_counts, str(dict(medium.get("summary", {})).get("reason_code") or ""))
    count_reason(reason_counts, str(dict(schedule.get("summary", {})).get("reason_code") or ""))

    recent_failures: List[Dict[str, Any]] = []
    history_runs = list(dict(canary_ops.get("history", {})).get("runs", [])) if isinstance(dict(canary_ops.get("history", {})).get("runs"), list) else []
    if not history_runs:
        history_path = (canary_ops_path.parent / "provider_canary_history.json").resolve()
        hist_doc = read_json_if_exists(history_path)
        history_runs = list(hist_doc.get("runs", [])) if isinstance(hist_doc.get("runs"), list) else []
    for row in reversed(history_runs):
        st = str(row.get("status") or "").upper()
        if st in {"FAIL", "WARN", "SKIP"}:
            recent_failures.append(
                {
                    "captured_at_utc": str(row.get("captured_at_utc") or ""),
                    "status": st,
                    "reason_code": str(row.get("reason_code") or ""),
                }
            )
        if len(recent_failures) >= max(1, int(args.recent_limit)):
            break

    rollback_command = str(dict(canary_base.get("rollback", {})).get("command") or "")
    if not rollback_command:
        rollback_command = str(dict(canary_ops.get("base", {})).get("summary", {}).get("rollback_command") or "")

    top_rows = [{"reason_code": key, "count": count} for key, count in top_reason_codes(reason_counts)]
    alerts = len(top_rows)

    if len(missing_inputs) == 4:
        status = "FAIL"
        reason_code = REASON_ALL_INPUTS_MISSING
    elif missing_inputs:
        status = "WARN"
        reason_code = REASON_PARTIAL_INPUTS_MISSING
    elif alerts > 0:
        status = "WARN"
        reason_code = REASON_TRIAGE_ALERT
    else:
        status = "PASS"
        reason_code = ""

    if status == "FAIL":
        emit("ERROR", f"triage status=FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"triage status=WARN reason={reason_code}", events)
    else:
        emit("OK", "triage status=PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s27-incident-triage-pack-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": inputs,
        "missing_inputs": missing_inputs,
        "top_reasons": top_rows,
        "recent_failures": recent_failures,
        "rollback_command": rollback_command,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "missing_inputs": len(missing_inputs),
            "alerts": alerts,
        },
        "artifact_names": {
            "json": "incident_triage_pack_latest.json",
            "md": "incident_triage_pack_latest.md",
        },
    }

    out_json = out_dir / "incident_triage_pack_latest.json"
    out_md = out_dir / "incident_triage_pack_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
