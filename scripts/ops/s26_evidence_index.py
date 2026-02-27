#!/usr/bin/env python3
"""
S26-08 evidence index.

Goal:
- Collect S26 evidence pointers/status into one navigable index.
- Expose missing/failed phases early for release decisions.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s26-08"

PHASE_ARTIFACTS: List[Tuple[str, str]] = [
    ("S26-01", "docs/evidence/s26-01/provider_canary_latest.json"),
    ("S26-02", "docs/evidence/s26-02/medium_eval_wall_latest.json"),
    ("S26-03", "docs/evidence/s26-03/rollback_artifact_latest.json"),
    ("S26-04", "docs/evidence/s26-04/orchestration_core_latest.json"),
    ("S26-05", "docs/evidence/s26-05/regression_safety_latest.json"),
    ("S26-06", "docs/evidence/s26-06/acceptance_wall_latest.json"),
    ("S26-07", "docs/evidence/s26-07/reliability_report_latest.json"),
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


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# S26-08 Evidence Index (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- phases_total: `{summary.get('phases_total', 0)}`")
    lines.append(f"- present_missing: `{summary.get('present_count', 0)}/{summary.get('missing_count', 0)}`")
    lines.append(f"- failed_warn: `{summary.get('failed_count', 0)}/{summary.get('warn_count', 0)}`")
    lines.append("")
    lines.append("## Index")
    lines.append("")
    for row in payload.get("phases", []):
        lines.append(
            f"- {row.get('phase')}: status=`{row.get('status')}` captured=`{row.get('captured_at_utc')}` artifact=`{row.get('artifact')}`"
        )
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-08 Evidence Index")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- present_missing: {summary.get('present_count', 0)}/{summary.get('missing_count', 0)}")
    lines.append(f"- failed_warn: {summary.get('failed_count', 0)}/{summary.get('warn_count', 0)}")
    lines.append(f"- artifact: docs/evidence/s26-08/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-evidence-index", obs_root=args.obs_root)

    rows: List[Dict[str, Any]] = []
    failed_count = 0
    warn_count = 0
    missing_count = 0

    for phase, rel_artifact in PHASE_ARTIFACTS:
        path = (repo_root / rel_artifact).resolve()
        doc = read_json_if_exists(path)
        if not doc:
            missing_count += 1
            emit("ERROR", f"phase={phase} artifact missing path={path}", events)
            rows.append(
                {
                    "phase": phase,
                    "artifact": rel_artifact,
                    "present": False,
                    "status": "MISSING",
                    "schema_version": "",
                    "captured_at_utc": "",
                }
            )
            continue

        summary = dict(doc.get("summary", {}))
        status = str(summary.get("status") or "PASS")
        if status == "FAIL":
            failed_count += 1
            emit("ERROR", f"phase={phase} status=FAIL", events)
        elif status == "WARN":
            warn_count += 1
            emit("WARN", f"phase={phase} status=WARN", events)
        else:
            emit("OK", f"phase={phase} status={status}", events)

        rows.append(
            {
                "phase": phase,
                "artifact": rel_artifact,
                "present": True,
                "status": status,
                "schema_version": str(doc.get("schema_version") or ""),
                "captured_at_utc": str(doc.get("captured_at_utc") or ""),
            }
        )

    present_count = sum(1 for x in rows if bool(x.get("present")))
    status = "PASS"
    if missing_count > 0 or failed_count > 0:
        status = "FAIL"
    elif warn_count > 0:
        status = "WARN"

    payload: Dict[str, Any] = {
        "schema_version": "s26-evidence-index-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "phases": rows,
        "summary": {
            "status": status,
            "phases_total": len(rows),
            "present_count": present_count,
            "missing_count": missing_count,
            "failed_count": failed_count,
            "warn_count": warn_count,
        },
        "artifact_names": {
            "json": "evidence_index_latest.json",
            "md": "evidence_index_latest.md",
        },
    }

    out_json = out_dir / "evidence_index_latest.json"
    out_md = out_dir / "evidence_index_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
