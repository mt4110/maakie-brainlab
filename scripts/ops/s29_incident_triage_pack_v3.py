#!/usr/bin/env python3
"""
S29-04 incident triage pack v4.

Goal:
- Aggregate S29 recovery/taxonomy/notification signals into one triage payload.
- Keep next actions explicit for incident response.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s29-04"
DEFAULT_RECOVERY = "docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json"
DEFAULT_TAXONOMY = "docs/evidence/s29-02/taxonomy_pipeline_integration_latest.json"
DEFAULT_NOTIFY = "docs/evidence/s29-03/readiness_notify_multichannel_latest.json"
DEFAULT_TRIAGE_V1 = "docs/evidence/s27-04/incident_triage_pack_latest.json"

REASON_ALL_INPUTS_MISSING = "ALL_INPUTS_MISSING"
REASON_PARTIAL_INPUTS_MISSING = "PARTIAL_INPUTS_MISSING"
REASON_TRIAGE_ALERT = "TRIAGE_ALERT"

REASON_SEVERITY = {
    "RECOVERY_COMMAND_FAILED": "critical",
    "GATES_BLOCKED": "critical",
    "HARD_SLO_VIOLATION": "critical",
    "RECOVERY_REQUIRED": "major",
    "SKIP_RATE_HIGH": "major",
    "ATTEMPTED_CHANNELS_BELOW_MIN": "major",
    "UNKNOWN_RATIO_ABOVE_TARGET": "major",
    "NOTIFY_SEND_FAILED": "major",
    "NOTIFY_DRY_RUN": "minor",
    "BASELINE_CREATED": "minor",
    "INSUFFICIENT_RUNS": "minor",
}


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


def reason_severity(reason_code: str) -> str:
    code = str(reason_code or "").upper()
    return str(REASON_SEVERITY.get(code, "major"))


def dedupe_actions(actions: List[str], limit: int = 8) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in actions:
        text = str(raw or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(1, int(limit)):
            break
    return out


def build_priority_actions(recovery: Dict[str, Any], taxonomy: Dict[str, Any], notify: Dict[str, Any]) -> List[str]:
    actions: List[str] = []
    actions.extend([str(item) for item in list(recovery.get("recommended_actions", []))[:3]])
    actions.extend([str(item) for item in list(taxonomy.get("collection_actions", []))[:3]])
    for row in list(taxonomy.get("collection_actions_v2", []))[:3]:
        if not isinstance(row, dict):
            continue
        owner = str(row.get("owner") or "ops-triage")
        tax = str(row.get("taxonomy") or "unknown")
        target = int(row.get("target_cases", 0) or 0)
        actions.append(f"Owner {owner}: collect {target} labeled case(s) for taxonomy '{tax}'.")
    notify_sum = dict(notify.get("summary", {}))
    notify_reason = str(notify_sum.get("reason_code") or "")
    if str(notify_sum.get("status") or "") != "PASS":
        actions.append("Configure readiness webhook and enable re-delivery with retries.")
        if notify_reason:
            actions.append(f"Resolve notification issue: {notify_reason}.")
    return dedupe_actions(actions, limit=8)


def gather_exit_conditions(*docs: Dict[str, Any], limit: int = 8) -> List[str]:
    rows: List[str] = []
    for doc in docs:
        for item in list(dict(doc.get("constraints", {})).get("exit_conditions", [])):
            text = str(item or "").strip()
            if text:
                rows.append(text)
    return dedupe_actions(rows, limit=limit)


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    lines: List[str] = []
    lines.append("# S29-04 Incident Triage Pack v4 (Latest)")
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
    lines.append("## Priority Actions")
    lines.append("")
    for item in list(payload.get("priority_actions", [])):
        lines.append(f"- {item}")
    if not payload.get("priority_actions"):
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--recovery-json", default=DEFAULT_RECOVERY)
    parser.add_argument("--taxonomy-json", default=DEFAULT_TAXONOMY)
    parser.add_argument("--notify-json", default=DEFAULT_NOTIFY)
    parser.add_argument("--triage-v1-json", default=DEFAULT_TRIAGE_V1)
    parser.add_argument("--top-limit", type=int, default=5)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s29-incident-triage-pack-v4", obs_root=args.obs_root)

    recovery_path = (repo_root / str(args.recovery_json)).resolve()
    taxonomy_path = (repo_root / str(args.taxonomy_json)).resolve()
    notify_path = (repo_root / str(args.notify_json)).resolve()
    triage_v1_path = (repo_root / str(args.triage_v1_json)).resolve()

    recovery = read_json_if_exists(recovery_path)
    taxonomy = read_json_if_exists(taxonomy_path)
    notify = read_json_if_exists(notify_path)
    triage_v1 = read_json_if_exists(triage_v1_path)

    missing_inputs = [
        name
        for name, doc in [
            ("recovery_json", recovery),
            ("taxonomy_json", taxonomy),
            ("notify_json", notify),
            ("triage_v1_json", triage_v1),
        ]
        if not doc
    ]
    for name in missing_inputs:
        emit("WARN", f"missing input={name}", events)

    reason_counts: Dict[str, int] = {}
    count_reason(reason_counts, str(dict(recovery.get("summary", {})).get("reason_code") or ""))
    count_reason(reason_counts, str(dict(taxonomy.get("summary", {})).get("reason_code") or ""))
    count_reason(reason_counts, str(dict(notify.get("summary", {})).get("reason_code") or ""))
    for row in list(triage_v1.get("top_reasons", [])):
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason_code") or "")
        cnt = int(row.get("count", 0) or 0)
        if reason:
            reason_counts[reason] = int(reason_counts.get(reason, 0)) + max(1, cnt)

    priority_actions = build_priority_actions(recovery, taxonomy, notify)
    exit_conditions = gather_exit_conditions(recovery, taxonomy, notify)

    top_rows = [
        {"reason_code": key, "count": count, "severity": reason_severity(key)}
        for key, count in top_reason_codes(reason_counts, limit=int(args.top_limit))
    ]
    alerts = len(top_rows)
    alerts_by_severity = {"critical": 0, "major": 0, "minor": 0}
    for row in top_rows:
        sev = str(row.get("severity") or "major")
        if sev not in alerts_by_severity:
            sev = "major"
        alerts_by_severity[sev] = int(alerts_by_severity[sev]) + 1

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
        emit("ERROR", f"triage v4 FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"triage v4 WARN reason={reason_code}", events)
    else:
        emit("OK", "triage v4 PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s29-incident-triage-pack-v4",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "recovery_json": to_repo_rel(repo_root, recovery_path),
            "taxonomy_json": to_repo_rel(repo_root, taxonomy_path),
            "notify_json": to_repo_rel(repo_root, notify_path),
            "triage_v1_json": to_repo_rel(repo_root, triage_v1_path),
        },
        "missing_inputs": missing_inputs,
        "top_reasons": top_rows,
        "alerts_by_severity": alerts_by_severity,
        "priority_actions": priority_actions,
        "exit_conditions": exit_conditions,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "missing_inputs": len(missing_inputs),
            "alerts": alerts,
            "critical_alerts": int(alerts_by_severity.get("critical", 0)),
            "exit_condition_count": len(exit_conditions),
        },
        "artifact_names": {
            "json": "incident_triage_pack_v4_latest.json",
            "md": "incident_triage_pack_v4_latest.md",
        },
    }

    out_json = out_dir / "incident_triage_pack_v4_latest.json"
    out_md = out_dir / "incident_triage_pack_v4_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
