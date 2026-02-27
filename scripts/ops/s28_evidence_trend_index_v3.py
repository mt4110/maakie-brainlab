#!/usr/bin/env python3
"""
S28-08 evidence trend index v3.

Goal:
- Index S28-01..S28-07 latest artifacts.
- Track missing/failed/warn trends across runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s28-08"
DEFAULT_HISTORY_FILE = "evidence_trend_history_v3.json"

PHASE_ARTIFACTS: List[Tuple[str, str]] = [
    ("S28-01", "docs/evidence/s28-01/provider_canary_recovery_latest.json"),
    ("S28-02", "docs/evidence/s28-02/taxonomy_feedback_loop_latest.json"),
    ("S28-03", "docs/evidence/s28-03/readiness_notify_latest.json"),
    ("S28-04", "docs/evidence/s28-04/incident_triage_pack_v2_latest.json"),
    ("S28-05", "docs/evidence/s28-05/policy_drift_guard_v2_latest.json"),
    ("S28-06", "docs/evidence/s28-06/reliability_soak_v2_latest.json"),
    ("S28-07", "docs/evidence/s28-07/acceptance_wall_v3_latest.json"),
]


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


def infer_status(doc: Dict[str, Any]) -> str:
    summary = dict(doc.get("summary", {}))
    status = str(summary.get("status") or "").upper().strip()
    if status:
        return status
    readiness = str(summary.get("readiness") or "").upper().strip()
    if readiness == "READY":
        return "PASS"
    if readiness == "WARN_ONLY":
        return "WARN"
    if readiness == "BLOCKED":
        return "FAIL"
    return "PASS"


def parse_captured_at_epoch(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def is_stale(captured_at_utc: str, now_epoch: float, stale_hours: float) -> bool:
    if stale_hours <= 0:
        return False
    ts = parse_captured_at_epoch(captured_at_utc)
    if ts <= 0:
        return True
    age_sec = max(0.0, float(now_epoch) - ts)
    return age_sec > float(stale_hours) * 3600.0


def count_statuses(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {"present_count": 0, "missing_count": 0, "pass_count": 0, "warn_count": 0, "failed_count": 0, "stale_count": 0}
    for row in rows:
        if not bool(row.get("present")):
            out["missing_count"] += 1
            continue
        out["present_count"] += 1
        if bool(row.get("stale")):
            out["stale_count"] += 1
        st = str(row.get("status") or "").upper()
        if st == "FAIL":
            out["failed_count"] += 1
        elif st == "WARN":
            out["warn_count"] += 1
        else:
            out["pass_count"] += 1
    return out


def overall_status(counts: Dict[str, int]) -> str:
    if (
        int(counts.get("missing_count", 0)) > 0
        or int(counts.get("failed_count", 0)) > 0
        or int(counts.get("stale_count", 0)) > 0
    ):
        return "FAIL"
    if int(counts.get("warn_count", 0)) > 0:
        return "WARN"
    return "PASS"


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    lines: List[str] = []
    lines.append("# S28-08 Evidence Trend Index v3 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- present_missing: `{summary.get('present_count', 0)}/{summary.get('missing_count', 0)}`")
    lines.append(f"- pass_warn_fail: `{summary.get('pass_count', 0)}/{summary.get('warn_count', 0)}/{summary.get('failed_count', 0)}`")
    lines.append(f"- history_size: `{summary.get('history_size', 0)}`")
    lines.append("")
    lines.append("## Phase Statuses")
    lines.append("")
    for row in list(payload.get("phases", [])):
        lines.append(f"- {row.get('phase')}: `{row.get('status')}` artifact=`{row.get('artifact')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S28-08 Evidence Trend Index v3")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- present_missing: {summary.get('present_count', 0)}/{summary.get('missing_count', 0)}")
    lines.append(f"- pass_warn_fail: {summary.get('pass_count', 0)}/{summary.get('warn_count', 0)}/{summary.get('failed_count', 0)}")
    lines.append(f"- history_size: {summary.get('history_size', 0)}")
    lines.append(f"- artifact: docs/evidence/s28-08/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--history-file", default=DEFAULT_HISTORY_FILE)
    parser.add_argument("--max-history", type=int, default=100)
    parser.add_argument("--stale-hours", type=float, default=6.0)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s28-evidence-trend-index-v3", obs_root=args.obs_root)

    rows: List[Dict[str, Any]] = []
    now_epoch = time.time()
    for phase, rel_artifact in PHASE_ARTIFACTS:
        path = (repo_root / rel_artifact).resolve()
        doc = read_json_if_exists(path)
        if not doc:
            emit("ERROR", f"phase={phase} artifact missing path={path}", events)
            rows.append(
                {"phase": phase, "artifact": rel_artifact, "present": False, "status": "MISSING", "captured_at_utc": "", "stale": False}
            )
            continue
        status = infer_status(doc)
        captured = str(doc.get("captured_at_utc") or "")
        stale = is_stale(captured, now_epoch=now_epoch, stale_hours=float(args.stale_hours))
        level = "OK"
        if status == "FAIL":
            level = "ERROR"
        elif status == "WARN":
            level = "WARN"
        if stale:
            level = "ERROR"
        emit(level, f"phase={phase} status={status} stale={stale}", events)
        rows.append(
            {
                "phase": phase,
                "artifact": rel_artifact,
                "present": True,
                "status": status,
                "captured_at_utc": captured,
                "stale": stale,
            }
        )

    counts = count_statuses(rows)
    status = overall_status(counts)

    history_path = out_dir / str(args.history_file)
    history_doc = read_json_if_exists(history_path)
    snapshots = list(history_doc.get("snapshots", [])) if isinstance(history_doc.get("snapshots"), list) else []

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    snapshot = {
        "captured_at_utc": now,
        "status": status,
        "counts": counts,
        "phase_statuses": {row["phase"]: row["status"] for row in rows},
    }
    prev = snapshots[-1] if snapshots else {}
    snapshots.append(snapshot)
    max_history = max(1, int(args.max_history))
    if len(snapshots) > max_history:
        snapshots = snapshots[-max_history:]
    history_doc = {
        "schema_version": "s28-evidence-trend-history-v3",
        "updated_at_utc": now,
        "snapshots": snapshots,
    }
    history_path.write_text(json.dumps(history_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    deltas = {
        "missing_delta": int(counts.get("missing_count", 0)) - int(dict(prev.get("counts", {})).get("missing_count", 0)),
        "failed_delta": int(counts.get("failed_count", 0)) - int(dict(prev.get("counts", {})).get("failed_count", 0)),
        "warn_delta": int(counts.get("warn_count", 0)) - int(dict(prev.get("counts", {})).get("warn_count", 0)),
    }

    payload: Dict[str, Any] = {
        "schema_version": "s28-evidence-trend-index-v3",
        "captured_at_utc": now,
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])} ,
        "phases": rows,
        "history": {
            "path": to_repo_rel(repo_root, history_path),
            "size": len(snapshots),
            "deltas": deltas,
        },
        "summary": {
            "status": status,
            "history_size": len(snapshots),
            **counts,
        },
        "artifact_names": {"json": "evidence_trend_index_v3_latest.json", "md": "evidence_trend_index_v3_latest.md", "history": str(args.history_file)},
    }

    out_json = out_dir / "evidence_trend_index_v3_latest.json"
    out_md = out_dir / "evidence_trend_index_v3_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)
    emit("OK", f"history_json={history_path}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, **counts})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
