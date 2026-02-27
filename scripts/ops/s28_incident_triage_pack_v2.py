#!/usr/bin/env python3
"""
S28-04 incident triage pack v2.

Goal:
- Aggregate S28 recovery/taxonomy/notification signals into one triage payload.
- Keep next actions explicit for incident response.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s28-04"
DEFAULT_RECOVERY = "docs/evidence/s28-01/provider_canary_recovery_latest.json"
DEFAULT_TAXONOMY = "docs/evidence/s28-02/taxonomy_feedback_loop_latest.json"
DEFAULT_NOTIFY = "docs/evidence/s28-03/readiness_notify_latest.json"
DEFAULT_TRIAGE_V1 = "docs/evidence/s27-04/incident_triage_pack_latest.json"

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
    lines.append("# S28-04 Incident Triage Pack v2 (Latest)")
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
    run_dir, meta, events = make_run_context(repo_root, tool="s28-incident-triage-pack-v2", obs_root=args.obs_root)

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

    priority_actions: List[str] = []
    for item in list(recovery.get("recommended_actions", []))[:2]:
        priority_actions.append(str(item))
    for item in list(taxonomy.get("collection_actions", []))[:2]:
        priority_actions.append(str(item))
    notify_sum = dict(notify.get("summary", {}))
    if str(notify_sum.get("status") or "") != "PASS":
        priority_actions.append("Configure readiness webhook and re-run notification dispatch.")

    top_rows = [{"reason_code": key, "count": count} for key, count in top_reason_codes(reason_counts, limit=int(args.top_limit))]
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
        emit("ERROR", f"triage v2 FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"triage v2 WARN reason={reason_code}", events)
    else:
        emit("OK", "triage v2 PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s28-incident-triage-pack-v2",
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
        "priority_actions": priority_actions,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "missing_inputs": len(missing_inputs),
            "alerts": alerts,
        },
        "artifact_names": {
            "json": "incident_triage_pack_v2_latest.json",
            "md": "incident_triage_pack_v2_latest.md",
        },
    }

    out_json = out_dir / "incident_triage_pack_v2_latest.json"
    out_md = out_dir / "incident_triage_pack_v2_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
