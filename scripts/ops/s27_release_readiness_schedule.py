#!/usr/bin/env python3
"""
S27-03 release readiness schedule wrapper.

Goal:
- Provide CI schedule-friendly readiness execution.
- Keep this phase non-blocking while still surfacing missing readiness as WARN/FAIL.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s27-03"
DEFAULT_PRIMARY_CMD = "python3 scripts/ops/s27_slo_readiness.py"
DEFAULT_FALLBACK_CMD = "python3 scripts/ops/s26_release_readiness.py"
DEFAULT_PRIMARY_ARTIFACT = "docs/evidence/s27-09/slo_readiness_latest.json"
DEFAULT_FALLBACK_ARTIFACT = "docs/evidence/s26-09/release_readiness_latest.json"
DEFAULT_TIMEOUT_SEC = 300

REASON_PRIMARY_FAILED = "PRIMARY_FAILED"
REASON_PRIMARY_AND_FALLBACK_FAILED = "PRIMARY_AND_FALLBACK_FAILED"
REASON_FALLBACK_USED = "FALLBACK_USED"
REASON_READINESS_MISSING = "READINESS_MISSING"


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


def run_command(repo_root: Path, run_dir: Path, label: str, command: str, timeout_sec: int) -> Dict[str, Any]:
    stdout_path = run_dir / f"{label}.stdout.log"
    stderr_path = run_dir / f"{label}.stderr.log"
    try:
        cp = subprocess.run(
            shlex.split(command),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_sec)),
            check=False,
        )
    except Exception as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        return {
            "label": label,
            "command": command,
            "returncode": 1,
            "status": "FAIL",
            "stdout_log": to_repo_rel(repo_root, stdout_path),
            "stderr_log": to_repo_rel(repo_root, stderr_path),
            "error": str(exc),
        }

    stdout_path.write_text(cp.stdout or "", encoding="utf-8")
    stderr_path.write_text(cp.stderr or "", encoding="utf-8")
    return {
        "label": label,
        "command": command,
        "returncode": int(cp.returncode),
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "stdout_log": to_repo_rel(repo_root, stdout_path),
        "stderr_log": to_repo_rel(repo_root, stderr_path),
        "error": "",
    }


def summarize_readiness(doc: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(doc.get("summary", {}))
    readiness = str(summary.get("readiness") or summary.get("status") or "")
    blocked = summary.get("blocked_total")
    if blocked is None:
        blocked = summary.get("blocked_gates")
    if blocked is None:
        blocked = summary.get("failed_count", 0)
    try:
        blocked_int = int(blocked)
    except Exception:
        blocked_int = 0
    return {
        "readiness": readiness,
        "blocked": blocked_int,
        "raw_summary": summary,
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    lines: List[str] = []
    lines.append("# S27-03 Release Readiness Schedule (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- Trigger: `{payload.get('trigger', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- readiness: `{summary.get('readiness', '')}`")
    lines.append(f"- blocked: `{summary.get('blocked_gates', 0)}`")
    lines.append(f"- source: `{summary.get('readiness_source', '')}`")
    lines.append("")
    lines.append("## Commands")
    lines.append("")
    for row in list(payload.get("commands", [])):
        lines.append(f"- {row.get('label')}: `{row.get('status')}` rc=`{row.get('returncode')}` cmd=`{row.get('command')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S27-03 Release Readiness Schedule")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- readiness: {summary.get('readiness', '')}")
    lines.append(f"- blocked_gates: {summary.get('blocked_gates', 0)}")
    lines.append(f"- source: {summary.get('readiness_source', '')}")
    lines.append(f"- artifact: docs/evidence/s27-03/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--trigger", default="")
    parser.add_argument("--primary-cmd", default=DEFAULT_PRIMARY_CMD)
    parser.add_argument("--fallback-cmd", default=DEFAULT_FALLBACK_CMD)
    parser.add_argument("--primary-artifact", default=DEFAULT_PRIMARY_ARTIFACT)
    parser.add_argument("--fallback-artifact", default=DEFAULT_FALLBACK_ARTIFACT)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s27-release-readiness-schedule", obs_root=args.obs_root)

    trigger = str(args.trigger or os.environ.get("GITHUB_EVENT_NAME") or "manual")
    commands: List[Dict[str, Any]] = []

    if args.skip_run:
        emit("SKIP", "readiness command execution skipped", events)
    else:
        primary = run_command(repo_root, run_dir, "primary", str(args.primary_cmd), int(args.timeout_sec))
        commands.append(primary)
        level = "OK" if primary["status"] == "PASS" else "ERROR"
        emit(level, f"primary status={primary['status']} rc={primary['returncode']}", events)
        if primary["status"] != "PASS":
            fallback = run_command(repo_root, run_dir, "fallback", str(args.fallback_cmd), int(args.timeout_sec))
            commands.append(fallback)
            fallback_level = "OK" if fallback["status"] == "PASS" else "ERROR"
            emit(fallback_level, f"fallback status={fallback['status']} rc={fallback['returncode']}", events)

    primary_artifact_path = (repo_root / str(args.primary_artifact)).resolve()
    fallback_artifact_path = (repo_root / str(args.fallback_artifact)).resolve()
    primary_doc = read_json_if_exists(primary_artifact_path)
    fallback_doc = read_json_if_exists(fallback_artifact_path)

    status = "PASS"
    reason_code = ""
    readiness_source = ""
    readiness_summary: Dict[str, Any] = {"readiness": "", "blocked": 0}
    primary_status = str(commands[0].get("status") or "") if len(commands) >= 1 else ""
    fallback_status = str(commands[1].get("status") or "") if len(commands) >= 2 else ""

    if primary_doc:
        readiness_summary = summarize_readiness(primary_doc)
        readiness_source = to_repo_rel(repo_root, primary_artifact_path)
        if primary_status == "FAIL" and fallback_status == "FAIL":
            status = "FAIL"
            reason_code = REASON_PRIMARY_AND_FALLBACK_FAILED
        elif primary_status == "FAIL":
            status = "WARN"
            reason_code = REASON_PRIMARY_FAILED
    elif fallback_doc:
        readiness_summary = summarize_readiness(fallback_doc)
        readiness_source = to_repo_rel(repo_root, fallback_artifact_path)
        status = "WARN"
        reason_code = REASON_FALLBACK_USED
    else:
        status = "FAIL"
        reason_code = REASON_READINESS_MISSING

    if status == "FAIL":
        emit("ERROR", f"schedule status=FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"schedule status=WARN reason={reason_code}", events)
    else:
        emit("OK", "schedule status=PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s27-release-readiness-schedule-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "trigger": trigger,
        "commands": commands,
        "inputs": {
            "primary_artifact": to_repo_rel(repo_root, primary_artifact_path),
            "fallback_artifact": to_repo_rel(repo_root, fallback_artifact_path),
        },
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "readiness": readiness_summary.get("readiness", ""),
            "blocked_gates": readiness_summary.get("blocked", 0),
            "readiness_source": readiness_source,
        },
        "artifact_names": {
            "json": "release_readiness_schedule_latest.json",
            "md": "release_readiness_schedule_latest.md",
        },
    }

    out_json = out_dir / "release_readiness_schedule_latest.json"
    out_md = out_dir / "release_readiness_schedule_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "trigger": trigger})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
