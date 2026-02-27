#!/usr/bin/env python3
"""
S26-03 rollback artifact collector.

Goal:
- Always collect rollback execution evidence as CI-friendly artifacts.
- Keep rollback command in one place and executable on demand.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s26-03"
DEFAULT_CANARY = "docs/evidence/s26-01/provider_canary_latest.json"
DEFAULT_MEDIUM = "docs/evidence/s26-02/medium_eval_wall_latest.json"
DEFAULT_TIMEOUT_SEC = 180
DEFAULT_ROLLBACK_COMMAND = "python3 scripts/ops/s25_langchain_poc.py --mode rollback-only"

REASON_ROLLBACK_FAILED = "ROLLBACK_FAILED"


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    rel_text = rel.as_posix()
    if ".." in Path(rel_text).parts:
        return ""
    return rel_text


def read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    exec_info = payload.get("rollback_execution", {})
    lines: List[str] = []
    lines.append("# S26-03 Rollback Artifact (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- overall_status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- rollback_returncode: `{exec_info.get('returncode', '')}`")
    lines.append("")
    lines.append("## Upstream")
    lines.append("")
    lines.append(f"- canary_status: `{payload.get('upstream', {}).get('canary_status', '')}`")
    lines.append(f"- medium_status: `{payload.get('upstream', {}).get('medium_status', '')}`")
    lines.append("")
    lines.append("## Rollback")
    lines.append("")
    lines.append(f"- command: `{payload.get('rollback_command', '')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-03 Rollback Artifact")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- rollback_command: {payload.get('rollback_command', '')}")
    lines.append(f"- rollback_returncode: {exec_info.get('returncode', '')}")
    lines.append(f"- artifact: docs/evidence/s26-03/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--canary-json", default=DEFAULT_CANARY)
    parser.add_argument("--medium-json", default=DEFAULT_MEDIUM)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--rollback-command", default="")
    parser.add_argument("--skip-exec", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-rollback-artifact", obs_root=args.obs_root)

    canary_path = (repo_root / args.canary_json).resolve()
    medium_path = (repo_root / args.medium_json).resolve()
    canary = read_json_if_exists(canary_path)
    medium = read_json_if_exists(medium_path)

    command = str(args.rollback_command or "").strip()
    if not command:
        command = str(dict(canary.get("rollback", {})).get("command") or "").strip()
    if not command:
        command = DEFAULT_ROLLBACK_COMMAND

    emit("OK", f"canary_json_exists={canary_path.exists()}", events)
    emit("OK", f"medium_json_exists={medium_path.exists()}", events)
    emit("OK", f"rollback_command={command}", events)

    exec_info: Dict[str, Any] = {"returncode": "", "stdout_log": "", "stderr_log": "", "error": ""}
    status = "PASS"
    reason_code = ""

    if args.skip_exec:
        emit("SKIP", "rollback execution skipped by flag", events)
        exec_info["returncode"] = "SKIP"
    else:
        stdout_path = run_dir / "rollback.stdout.log"
        stderr_path = run_dir / "rollback.stderr.log"
        try:
            cmd = shlex.split(command)
            cp = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=max(1, int(args.timeout_sec)),
                check=False,
            )
            stdout_path.write_text(cp.stdout or "", encoding="utf-8")
            stderr_path.write_text(cp.stderr or "", encoding="utf-8")
            exec_info["returncode"] = int(cp.returncode)
            exec_info["stdout_log"] = to_repo_rel(repo_root, stdout_path)
            exec_info["stderr_log"] = to_repo_rel(repo_root, stderr_path)
            if cp.returncode == 0:
                emit("OK", "rollback execution passed", events)
            else:
                emit("ERROR", f"rollback execution failed returncode={cp.returncode}", events)
                status = "FAIL"
                reason_code = REASON_ROLLBACK_FAILED
        except Exception as exc:
            emit("ERROR", f"rollback execution exception err={exc}", events)
            exec_info["error"] = str(exc)
            status = "FAIL"
            reason_code = REASON_ROLLBACK_FAILED

    payload: Dict[str, Any] = {
        "schema_version": "s26-rollback-artifact-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "upstream": {
            "canary_json": to_repo_rel(repo_root, canary_path),
            "canary_status": str(dict(canary.get("summary", {})).get("status") or ""),
            "medium_json": to_repo_rel(repo_root, medium_path),
            "medium_status": str(dict(medium.get("summary", {})).get("status") or ""),
        },
        "rollback_command": command,
        "rollback_execution": exec_info,
        "summary": {"status": status, "reason_code": reason_code},
        "artifact_names": {"json": "rollback_artifact_latest.json", "md": "rollback_artifact_latest.md"},
    }

    json_path = out_dir / "rollback_artifact_latest.json"
    md_path = out_dir / "rollback_artifact_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={json_path}", events)
    emit("OK", f"artifact_md={md_path}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
