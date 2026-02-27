#!/usr/bin/env python3
"""
S26-04 orchestration core runner.

Goal:
- Run S26-01 -> S26-03 in order.
- Keep stopless execution and persist one summary artifact.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s26-04"
DEFAULT_TIMEOUT_SEC = 300

STEP_PROVIDER = "s26-provider-canary"
STEP_MEDIUM = "s26-medium-eval-wall"
STEP_ROLLBACK = "s26-rollback-artifact"


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


def run_step(
    repo_root: Path,
    run_dir: Path,
    name: str,
    exec_cmd: List[str],
    display_cmd: List[str],
    timeout_sec: int,
) -> Dict[str, Any]:
    stdout_path = run_dir / f"{name}.stdout.log"
    stderr_path = run_dir / f"{name}.stderr.log"
    try:
        cp = subprocess.run(
            exec_cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=max(1, timeout_sec),
            check=False,
        )
    except Exception as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        return {
            "name": name,
            "command": display_cmd,
            "returncode": 1,
            "status": "FAIL",
            "error": str(exc),
            "stdout_log": to_repo_rel(repo_root, stdout_path),
            "stderr_log": to_repo_rel(repo_root, stderr_path),
        }

    stdout_path.write_text(cp.stdout or "", encoding="utf-8")
    stderr_path.write_text(cp.stderr or "", encoding="utf-8")
    return {
        "name": name,
        "command": display_cmd,
        "returncode": int(cp.returncode),
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "error": "",
        "stdout_log": to_repo_rel(repo_root, stdout_path),
        "stderr_log": to_repo_rel(repo_root, stderr_path),
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines: List[str] = []
    lines.append("# S26-04 Orchestration Core (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- overall_status: `{summary.get('status', '')}`")
    lines.append(f"- failed_steps: `{summary.get('failed_steps', 0)}`")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    for step in list(payload.get("steps", [])):
        lines.append(
            f"- {step.get('name')}: `{step.get('status')}` (rc={step.get('returncode')})"
        )
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-04 Orchestration Core")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- failed_steps: {summary.get('failed_steps', 0)}")
    lines.append(f"- artifact: docs/evidence/s26-04/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-orchestration-core", obs_root=args.obs_root)

    steps: List[Dict[str, Any]] = []
    commands = [
        (
            STEP_PROVIDER,
            ["python3", "scripts/ops/s26_provider_canary.py"],
            ["python3", "scripts/ops/s26_provider_canary.py"],
        ),
        (
            STEP_MEDIUM,
            ["python3", "scripts/ops/s26_medium_eval_wall.py"],
            ["python3", "scripts/ops/s26_medium_eval_wall.py"],
        ),
        (
            STEP_ROLLBACK,
            ["python3", "scripts/ops/s26_rollback_artifact.py"],
            ["python3", "scripts/ops/s26_rollback_artifact.py"],
        ),
    ]
    for name, exec_cmd, display_cmd in commands:
        emit("OK", f"run step={name}", events)
        out = run_step(
            repo_root,
            run_dir,
            name,
            exec_cmd=exec_cmd,
            display_cmd=display_cmd,
            timeout_sec=int(args.timeout_sec),
        )
        steps.append(out)
        level = "OK" if out["status"] == "PASS" else "ERROR"
        emit(level, f"step={name} status={out['status']} rc={out['returncode']}", events)

    canary = read_json_if_exists((repo_root / "docs/evidence/s26-01/provider_canary_latest.json").resolve())
    medium = read_json_if_exists((repo_root / "docs/evidence/s26-02/medium_eval_wall_latest.json").resolve())
    rollback = read_json_if_exists((repo_root / "docs/evidence/s26-03/rollback_artifact_latest.json").resolve())

    failed_steps = sum(1 for item in steps if str(item.get("status")) != "PASS")
    status = "PASS" if failed_steps == 0 else "FAIL"
    summary = {"status": status, "failed_steps": failed_steps}
    payload: Dict[str, Any] = {
        "schema_version": "s26-orchestration-core-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "steps": steps,
        "upstream_status": {
            "canary": str(dict(canary.get("summary", {})).get("status") or ""),
            "medium_eval_wall": str(dict(medium.get("summary", {})).get("status") or ""),
            "rollback_artifact": str(dict(rollback.get("summary", {})).get("status") or ""),
        },
        "summary": summary,
        "artifact_names": {"json": "orchestration_core_latest.json", "md": "orchestration_core_latest.md"},
    }

    json_path = out_dir / "orchestration_core_latest.json"
    md_path = out_dir / "orchestration_core_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={json_path}", events)
    emit("OK", f"artifact_md={md_path}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra=summary)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
