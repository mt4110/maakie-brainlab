#!/usr/bin/env python3
"""
S25-05 Regression Safety runner.

Purpose:
- Verify compatibility with existing verify commands.
- Detect contract break risk (e.g. milestone checks accidentally becoming required).
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
    "make verify-il",
    "bash ops/required_checks_sot.sh check",
    "python3 ops/ci/check_required_checks_contract.py",
    "python3 -m unittest -v tests/test_required_checks_contract.py",
]

FORBIDDEN_REQUIRED_CONTEXTS = ("milestone_required", "milestone_advisory")
DOC_SOT_RE = re.compile(r"<!--\s*required_checks_sot:v1(.*?)-->", re.S)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def run_command(cmd: str, repo_root: Path, log_path: Path) -> Dict[str, Any]:
    t0 = utc_now()
    cp = subprocess.run(["bash", "-lc", cmd], cwd=str(repo_root), capture_output=True, text=True, check=False)
    t1 = utc_now()
    output = (cp.stdout or "") + (cp.stderr or "")
    log_path.write_text(output, encoding="utf-8")
    return {
        "command": cmd,
        "rc": cp.returncode,
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "duration_sec": round((t1 - t0).total_seconds(), 3),
        "started_at_utc": t0.isoformat(),
        "ended_at_utc": t1.isoformat(),
        "log_path": str(log_path),
    }


def read_required_contexts(repo_root: Path) -> Tuple[List[str], List[str]]:
    docs_contexts: List[str] = []
    ruleset_contexts: List[str] = []

    docs_path = repo_root / "docs" / "ops" / "CI_REQUIRED_CHECKS.md"
    ruleset_path = repo_root / "ops" / "ruleset_required_status_checks.json"

    try:
        text = docs_path.read_text(encoding="utf-8")
        m = DOC_SOT_RE.search(text)
        if m:
            for raw in m.group(1).splitlines():
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                docs_contexts.append(s)
    except Exception:
        pass

    try:
        obj = json.loads(ruleset_path.read_text(encoding="utf-8"))
        items = obj.get("required_status_checks", [])
        if isinstance(items, list):
            ruleset_contexts = [str(x).strip() for x in items if str(x).strip()]
    except Exception:
        pass

    return sorted(set(docs_contexts)), sorted(set(ruleset_contexts))


def detect_contract_breaks(docs_contexts: List[str], ruleset_contexts: List[str]) -> List[str]:
    issues: List[str] = []
    for forbidden in FORBIDDEN_REQUIRED_CONTEXTS:
        if forbidden in docs_contexts:
            issues.append(f"forbidden context present in docs SOT: {forbidden}")
        if forbidden in ruleset_contexts:
            issues.append(f"forbidden context present in ruleset SOT: {forbidden}")
    return issues


def build_markdown(result: Dict[str, Any]) -> str:
    summary = result["summary"]
    lines: List[str] = []
    lines.append("# S25-05 Regression Safety (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{result['captured_at_utc']}`")
    lines.append(f"- Branch: `{result['git']['branch']}`")
    lines.append(f"- HeadSHA: `{result['git']['head']}`")
    lines.append("")
    lines.append("## Safety Metrics")
    lines.append("")
    lines.append(f"- Verify compatibility: `{summary['passed_commands']}/{summary['total_commands']}` commands passed")
    lines.append(f"- Contract breaks: `{len(summary['contract_breaks'])}`")
    lines.append(f"- Speed(total): `{summary['total_duration_sec']} sec`")
    lines.append("")
    lines.append("## Commands")
    lines.append("")
    for item in result["commands"]:
        lines.append(f"- `{item['status']}` `{item['duration_sec']}s` `{item['command']}`")
    lines.append("")
    lines.append("## Contract Check")
    lines.append("")
    if summary["contract_breaks"]:
        for issue in summary["contract_breaks"]:
            lines.append(f"- ERROR: {issue}")
    else:
        lines.append("- OK: no forbidden required contexts detected")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-05 Regression Safety")
    lines.append(f"- verify_compatibility: {summary['passed_commands']}/{summary['total_commands']} commands passed")
    lines.append(f"- contract_breaks: {len(summary['contract_breaks'])}")
    lines.append(f"- speed: total {summary['total_duration_sec']} sec")
    lines.append(f"- artifact: docs/evidence/s25-05/{result['artifact_names']['json']}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s25-05", help="Output directory")
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT, help="Observability root directory")
    parser.add_argument("--command", action="append", default=[], help="Override command list")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="regression-safety", obs_root=args.obs_root)

    commands = args.command if args.command else DEFAULT_COMMANDS
    command_results: List[Dict[str, Any]] = []
    stop = 0
    for i, cmd in enumerate(commands, start=1):
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", cmd).strip("_").lower()
        log_path = run_dir / f"{i:02d}_{slug[:60]}.log"
        emit("OK", f"run[{i}]={cmd}", events)
        res = run_command(cmd, repo_root=repo_root, log_path=log_path)
        command_results.append(res)
        if res["status"] == "PASS":
            emit("OK", f"done[{i}] rc=0 duration={res['duration_sec']}s", events)
        else:
            stop = 1
            emit("ERROR", f"done[{i}] rc={res['rc']} duration={res['duration_sec']}s", events)

    docs_contexts, ruleset_contexts = read_required_contexts(repo_root)
    contract_breaks = detect_contract_breaks(docs_contexts, ruleset_contexts)
    if contract_breaks:
        stop = 1
        for issue in contract_breaks:
            emit("ERROR", issue, events)
    else:
        emit("OK", "no forbidden required contexts detected", events)

    total_sec = round(sum(float(x["duration_sec"]) for x in command_results), 3)
    passed = sum(1 for x in command_results if x["status"] == "PASS")

    payload: Dict[str, Any] = {
        "schema_version": "s25-regression-safety-v1",
        "captured_at_utc": utc_now().isoformat(),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "summary": {
            "total_commands": len(command_results),
            "passed_commands": passed,
            "failed_commands": len(command_results) - passed,
            "total_duration_sec": total_sec,
            "contract_breaks": contract_breaks,
        },
        "required_contexts": {
            "docs_sot": docs_contexts,
            "ruleset_sot": ruleset_contexts,
        },
        "commands": command_results,
        "artifact_names": {
            "json": "regression_safety_latest.json",
            "md": "regression_safety_latest.md",
            "run_dir": str(run_dir),
        },
        "stop": stop,
    }

    out_json = out_dir / "regression_safety_latest.json"
    out_md = out_dir / "regression_safety_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"regression_json={out_json}", events)
    emit("OK", f"regression_md={out_md}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    if stop == 0:
        emit("OK", "regression_safety completed", events)
    else:
        emit("WARN", "regression_safety completed with failures", events)

    events_path = write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "regression_json": str(out_json),
            "regression_md": str(out_md),
            "stop": stop,
            "commands_total": len(command_results),
        },
    )
    print(f"OK: obs_events={events_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
