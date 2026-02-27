#!/usr/bin/env python3
"""
S26-05 regression safety runner.

Goal:
- Verify S26 core scripts/tests still execute in lightweight mode.
- Keep milestone/non-blocking contract visible in docs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_COMMANDS = [
    "make ops-now",
    "python3 -m unittest -v tests/test_s26_provider_canary.py",
    "python3 -m unittest -v tests/test_s26_medium_eval_wall.py",
    "python3 -m unittest -v tests/test_s26_rollback_artifact.py",
    "python3 -m unittest -v tests/test_s26_orchestration_core.py",
    "python3 -m unittest -v tests/test_s26_regression_safety.py",
    "python3 -m unittest -v tests/test_s26_acceptance_wall.py",
    "python3 -m unittest -v tests/test_s26_reliability_report.py",
    "python3 -m unittest -v tests/test_s26_evidence_index.py",
    "python3 -m unittest -v tests/test_s26_release_readiness.py",
    "python3 -m unittest -v tests/test_s26_closeout.py",
]

DEFAULT_DOCS = [
    "docs/ops/S26-01-S26-02-THREAD-V1_PLAN.md",
    "docs/ops/S26-01-S26-02-THREAD-V1_TASK.md",
]

NON_BLOCKING_RX = re.compile(r"non-?blocking", re.I)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


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


def run_command(cmd: str, repo_root: Path, log_path: Path) -> Dict[str, Any]:
    t0 = utc_now()
    cp = subprocess.run(["bash", "-lc", cmd], cwd=str(repo_root), capture_output=True, text=True, check=False)
    t1 = utc_now()
    output = (cp.stdout or "") + (cp.stderr or "")
    log_path.write_text(output, encoding="utf-8")
    return {
        "command": cmd,
        "rc": int(cp.returncode),
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "duration_sec": round((t1 - t0).total_seconds(), 3),
        "started_at_utc": t0.isoformat(),
        "ended_at_utc": t1.isoformat(),
        "log_path": to_repo_rel(repo_root, log_path),
    }


def read_contract_markers(repo_root: Path, rel_paths: List[str]) -> Tuple[List[str], List[str]]:
    markers: List[str] = []
    read_errors: List[str] = []
    for rel in rel_paths:
        p = (repo_root / rel).resolve()
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as exc:
            read_errors.append(f"read failed path={rel} err={exc}")
            continue
        if NON_BLOCKING_RX.search(text):
            markers.append(rel)
    return markers, read_errors


def detect_contract_breaks(marker_files: List[str], expected_min: int = 1) -> List[str]:
    issues: List[str] = []
    if len(marker_files) < expected_min:
        issues.append("non-blocking contract marker not found in docs")
    return issues


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# S26-05 Regression Safety (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload['captured_at_utc']}`")
    lines.append(f"- Branch: `{payload['git']['branch']}`")
    lines.append(f"- HeadSHA: `{payload['git']['head']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- command_passed: `{summary['passed_commands']}/{summary['total_commands']}`")
    lines.append(f"- contract_breaks: `{len(summary['contract_breaks'])}`")
    lines.append(f"- total_duration_sec: `{summary['total_duration_sec']}`")
    lines.append("")
    lines.append("## Commands")
    lines.append("")
    for item in payload["commands"]:
        lines.append(f"- {item['status']}: `{item['command']}` (`{item['duration_sec']}s`) rc={item['rc']}")
    lines.append("")
    lines.append("## Contract")
    lines.append("")
    if summary["contract_breaks"]:
        for issue in summary["contract_breaks"]:
            lines.append(f"- ERROR: {issue}")
    else:
        lines.append("- OK: non-blocking marker detected")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-05 Regression Safety")
    lines.append(f"- command_passed: {summary['passed_commands']}/{summary['total_commands']}")
    lines.append(f"- contract_breaks: {len(summary['contract_breaks'])}")
    lines.append(f"- total_duration_sec: {summary['total_duration_sec']}")
    lines.append(f"- artifact: docs/evidence/s26-05/{payload['artifact_names']['json']}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s26-05")
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--command", action="append", default=[])
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-regression-safety", obs_root=args.obs_root)

    commands = list(args.command) if args.command else list(DEFAULT_COMMANDS)
    command_results: List[Dict[str, Any]] = []
    stop = 0

    for idx, cmd in enumerate(commands, start=1):
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", cmd).strip("_").lower()
        log_path = run_dir / f"{idx:02d}_{slug[:64]}.log"
        emit("OK", f"run[{idx}]={cmd}", events)
        result = run_command(cmd, repo_root=repo_root, log_path=log_path)
        command_results.append(result)
        if result["status"] == "PASS":
            emit("OK", f"done[{idx}] rc=0 duration={result['duration_sec']}s", events)
        else:
            stop = 1
            emit("ERROR", f"done[{idx}] rc={result['rc']} duration={result['duration_sec']}s", events)

    marker_files, read_errors = read_contract_markers(repo_root, DEFAULT_DOCS)
    for err in read_errors:
        stop = 1
        emit("ERROR", err, events)
    contract_breaks = detect_contract_breaks(marker_files)
    if contract_breaks:
        stop = 1
        for issue in contract_breaks:
            emit("ERROR", issue, events)
    else:
        emit("OK", f"non-blocking marker files={marker_files}", events)

    total_duration_sec = round(sum(float(x["duration_sec"]) for x in command_results), 3)
    passed_commands = sum(1 for x in command_results if x["status"] == "PASS")

    payload: Dict[str, Any] = {
        "schema_version": "s26-regression-safety-v1",
        "captured_at_utc": utc_now().isoformat(),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "summary": {
            "total_commands": len(command_results),
            "passed_commands": passed_commands,
            "failed_commands": len(command_results) - passed_commands,
            "total_duration_sec": total_duration_sec,
            "contract_breaks": contract_breaks,
            "marker_files": marker_files,
        },
        "commands": command_results,
        "artifact_names": {
            "json": "regression_safety_latest.json",
            "md": "regression_safety_latest.md",
            "run_dir": to_repo_rel(repo_root, run_dir),
        },
        "stop": stop,
    }

    out_json = out_dir / "regression_safety_latest.json"
    out_md = out_dir / "regression_safety_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "stop": stop,
            "commands_total": len(command_results),
            "artifact_json": to_repo_rel(repo_root, out_json),
        },
    )
    return 0 if stop == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
