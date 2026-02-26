#!/usr/bin/env python3
"""
Generate S25-04 observability summary for PR body from latest obs runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, make_run_context, write_events, write_summary


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def collect_latest_tool_summaries(repo_root: Path, obs_root: str) -> Dict[str, Dict[str, Any]]:
    root = (repo_root / obs_root).resolve()
    found: Dict[str, Dict[str, Any]] = {}
    if not root.exists():
        return found
    for summary_path in sorted(root.glob("*/**/summary.json")):
        obj = _load_json(summary_path)
        if not obj:
            continue
        tool = str(obj.get("tool") or "unknown")
        now_ts = str(obj.get("captured_at_utc") or "")
        prev = found.get(tool)
        if prev is None or now_ts >= str(prev.get("captured_at_utc") or ""):
            found[tool] = obj
    return found


def write_observability_report(
    repo_root: Path,
    latest: Dict[str, Dict[str, Any]],
    baseline_path: Path,
    out_dir: Path,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline = _load_json(baseline_path)
    report = {
        "schema_version": "s25-obs-report-v1",
        "baseline_json": str(baseline_path),
        "tools": latest,
    }
    out_json = out_dir / "observability_latest.json"
    out_md = out_dir / "observability_latest.md"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# S25-04 Observability Summary (Latest)")
    lines.append("")
    lines.append(f"- baseline_json: `{baseline_path}`")
    lines.append("")
    lines.append("## Tools")
    lines.append("")
    if not latest:
        lines.append("- SKIP: no summary.json found under obs root")
    for tool, obj in sorted(latest.items()):
        counts = obj.get("counts", {})
        lines.append(
            f"- `{tool}` run=`{obj.get('run_id', '')}` "
            f"OK={counts.get('OK', 0)} WARN={counts.get('WARN', 0)} "
            f"ERROR={counts.get('ERROR', 0)} SKIP={counts.get('SKIP', 0)}"
        )
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-04 Observability")
    lines.append(f"- baseline: {baseline_path}")
    if latest:
        for tool, obj in sorted(latest.items()):
            counts = obj.get("counts", {})
            lines.append(
                f"- {tool}: run={obj.get('run_id', '')} "
                f"(OK={counts.get('OK', 0)} WARN={counts.get('WARN', 0)} "
                f"ERROR={counts.get('ERROR', 0)} SKIP={counts.get('SKIP', 0)})"
            )
    else:
        lines.append("- tools: no observation runs found")
    lines.append("- contract: levels=OK|WARN|ERROR|SKIP, path=.local/obs/s25-ops/<tool>/<run-id>/")
    lines.append("```")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {
        "json": str(out_json),
        "md": str(out_md),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT, help="Observability root directory")
    parser.add_argument("--out-dir", default="docs/evidence/s25-04", help="Output directory")
    parser.add_argument(
        "--baseline-json",
        default="docs/evidence/s25-03/baseline_latest.json",
        help="Baseline JSON reference",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    run_dir, meta, events = make_run_context(repo_root, tool="obs-pr-summary", obs_root=args.obs_root)

    baseline_path = (repo_root / args.baseline_json).resolve()
    if not baseline_path.exists():
        emit("WARN", f"baseline missing path={baseline_path}", events)
    latest = collect_latest_tool_summaries(repo_root, obs_root=args.obs_root)
    emit("OK", f"tools_found={len(latest)}", events)
    out = write_observability_report(
        repo_root=repo_root,
        latest=latest,
        baseline_path=baseline_path,
        out_dir=(repo_root / args.out_dir).resolve(),
    )
    emit("OK", f"observability_json={out['json']}", events)
    emit("OK", f"observability_md={out['md']}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"outputs": out})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
