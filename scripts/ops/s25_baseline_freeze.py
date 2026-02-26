#!/usr/bin/env python3
"""
S25-03 Baseline Freeze helper.

Runs a fixed command set, records durations/results, and writes:
- docs/evidence/s25-03/baseline_latest.json
- docs/evidence/s25-03/baseline_latest.md (PR-body friendly snippet)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.ops.obs_contract import (
    DEFAULT_OBS_ROOT,
    emit,
    git_out,
    make_run_context,
    write_events,
    write_summary,
)
from scripts.ops.s25_obs_pr_summary import collect_latest_tool_summaries, write_observability_report


DEFAULT_COMMANDS = [
    "make ops-now",
    "python3 -m unittest -v tests/test_current_point.py",
    "python3 tests/test_il_entry_smoke.py",
    "make verify-il-thread-v2",
    "python3 eval/run_eval.py --mode verify-only --provider mock --dataset rag-eval-wall-v1__seed-mini__v0001",
]

TESTS_RAN_RX = re.compile(r"Ran\s+(\d+)\s+tests?\s+in", re.I)
EVAL_RUN_DIR_RX = re.compile(r"Run artifacts saved to:\s*(.+)$")
OPS_PROGRESS_RX = re.compile(r"^OK:\s+progress=([0-9]+(?:\.[0-9]+)?%)\s*$", re.M)

def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(now: dt.datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%SZ")


def parse_unittest(output: str) -> Dict[str, Any]:
    m = TESTS_RAN_RX.search(output or "")
    if not m:
        return {}
    tests_ran = int(m.group(1))
    passed = "OK" in (output or "")
    return {"tests_ran": tests_ran, "passed": passed}


def parse_eval_summary(output: str, repo_root: Path) -> Dict[str, Any]:
    for line in (output or "").splitlines():
        m = EVAL_RUN_DIR_RX.search(line.strip())
        if not m:
            continue
        run_dir = Path(m.group(1).strip())
        if not run_dir.is_absolute():
            run_dir = (repo_root / run_dir).resolve()
        summary = run_dir / "summary.json"
        if summary.exists():
            try:
                obj = json.loads(summary.read_text(encoding="utf-8"))
                counts = obj.get("counts", {})
                passed = int(counts.get("PASS", 0))
                failed = int(counts.get("FAIL", 0))
                skipped = int(counts.get("SKIP", 0))
                total = passed + failed + skipped
                pass_rate = (passed / total) if total > 0 else None
                return {
                    "run_dir": str(run_dir),
                    "counts": counts,
                    "total": total,
                    "pass_rate": pass_rate,
                }
            except Exception:
                return {"run_dir": str(run_dir)}
        return {"run_dir": str(run_dir)}
    return {}


def parse_ops_progress(output: str) -> Optional[str]:
    m = OPS_PROGRESS_RX.search(output or "")
    if not m:
        return None
    return m.group(1)


def run_command(cmd: str, repo_root: Path, log_path: Path) -> Dict[str, Any]:
    t0 = utc_now()
    cp = subprocess.run(
        ["bash", "-lc", cmd],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    t1 = utc_now()
    output = (cp.stdout or "") + (cp.stderr or "")
    log_path.write_text(output, encoding="utf-8")

    result: Dict[str, Any] = {
        "command": cmd,
        "rc": cp.returncode,
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "started_at_utc": t0.isoformat(),
        "ended_at_utc": t1.isoformat(),
        "duration_sec": round((t1 - t0).total_seconds(), 3),
        "log_path": str(log_path),
    }

    if "unittest" in cmd:
        u = parse_unittest(output)
        if u:
            result["unittest"] = u
    if "run_eval.py" in cmd:
        ev = parse_eval_summary(output, repo_root=repo_root)
        if ev:
            result["eval"] = ev
    if "ops-now" in cmd:
        p = parse_ops_progress(output)
        if p:
            result["ops_progress"] = p
    return result


def build_markdown(baseline: Dict[str, Any]) -> str:
    summary = baseline["summary"]
    lines: List[str] = []
    lines.append("# S25-03 Baseline Freeze (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{baseline['captured_at_utc']}`")
    lines.append(f"- Branch: `{baseline['git']['branch']}`")
    lines.append(f"- HeadSHA: `{baseline['git']['head']}`")
    lines.append("")
    lines.append("## Baseline Metrics")
    lines.append("")
    lines.append(f"- Quality: `{summary['passed_commands']}/{summary['total_commands']}` commands passed")
    if summary.get("eval_pass_rate") is not None:
        lines.append(f"- Quality(eval pass rate): `{summary['eval_pass_rate_pct']}%`")
    lines.append(f"- Speed(total): `{summary['total_duration_sec']} sec`")
    lines.append(f"- Cost(command count): `{summary['total_commands']}`")
    if summary.get("ops_progress"):
        lines.append(f"- Current task progress at freeze: `{summary['ops_progress']}`")
    lines.append("")
    lines.append("## Commands")
    lines.append("")
    for item in baseline["commands"]:
        lines.append(f"- `{item['status']}` `{item['duration_sec']}s` `{item['command']}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-03 Baseline Freeze")
    lines.append(f"- quality: {summary['passed_commands']}/{summary['total_commands']} commands passed")
    if summary.get("eval_pass_rate") is not None:
        lines.append(f"- eval pass rate: {summary['eval_pass_rate_pct']}%")
    lines.append(f"- speed: total {summary['total_duration_sec']} sec")
    lines.append(f"- cost: {summary['total_commands']} commands")
    lines.append(f"- artifact: docs/evidence/s25-03/{baseline['artifact_names']['json']}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s25-03", help="Output directory")
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT, help="Observability root directory")
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="Command to run. If omitted, default command set is used.",
    )
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="baseline-freeze", obs_root=args.obs_root)

    now = utc_now()

    commands = args.command if args.command else DEFAULT_COMMANDS
    results: List[Dict[str, Any]] = []
    stop = 0
    for i, cmd in enumerate(commands, start=1):
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", cmd).strip("_").lower()
        log_path = run_dir / f"{i:02d}_{slug[:60]}.log"
        emit("OK", f"run[{i}]={cmd}", events)
        r = run_command(cmd, repo_root=repo_root, log_path=log_path)
        results.append(r)
        if r["status"] == "PASS":
            emit("OK", f"done[{i}] rc=0 duration={r['duration_sec']}s", events)
        else:
            stop = 1
            emit("ERROR", f"done[{i}] rc={r['rc']} duration={r['duration_sec']}s", events)

    total_sec = round(sum(float(x["duration_sec"]) for x in results), 3)
    passed_commands = sum(1 for x in results if x["status"] == "PASS")
    eval_pass_rate = None
    eval_pass_rate_pct = None
    ops_progress = None
    for x in results:
        if x.get("eval", {}).get("pass_rate") is not None:
            eval_pass_rate = float(x["eval"]["pass_rate"])
            eval_pass_rate_pct = round(eval_pass_rate * 100, 2)
        if x.get("ops_progress"):
            ops_progress = x["ops_progress"]

    baseline: Dict[str, Any] = {
        "schema_version": "s25-baseline-v1",
        "captured_at_utc": now.isoformat(),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "summary": {
            "total_commands": len(results),
            "passed_commands": passed_commands,
            "failed_commands": len(results) - passed_commands,
            "total_duration_sec": total_sec,
            "eval_pass_rate": eval_pass_rate,
            "eval_pass_rate_pct": eval_pass_rate_pct,
            "ops_progress": ops_progress,
        },
        "commands": results,
        "artifact_names": {
            "json": "baseline_latest.json",
            "md": "baseline_latest.md",
            "run_dir": str(run_dir),
        },
        "stop": stop,
    }

    latest_json = out_dir / "baseline_latest.json"
    latest_md = out_dir / "baseline_latest.md"
    latest_json.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_md.write_text(build_markdown(baseline), encoding="utf-8")

    emit("OK", f"baseline_json={latest_json}", events)
    emit("OK", f"baseline_md={latest_md}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    if stop == 0:
        emit("OK", "baseline_freeze completed", events)
    else:
        emit("WARN", f"baseline completed with failures; review {latest_json}", events)

    events_path = write_events(run_dir, events)
    obs_summary = write_summary(
        run_dir,
        meta,
        events,
        extra={
            "baseline_json": str(latest_json),
            "baseline_md": str(latest_md),
            "stop": stop,
            "commands_total": len(results),
        },
    )
    latest_tools = collect_latest_tool_summaries(repo_root, obs_root=args.obs_root)
    report_out = write_observability_report(
        repo_root=repo_root,
        latest=latest_tools,
        baseline_path=latest_json,
        out_dir=(repo_root / "docs" / "evidence" / "s25-04").resolve(),
    )
    print(f"OK: observability_json={report_out['json']}", flush=True)
    print(f"OK: observability_md={report_out['md']}", flush=True)

    print(f"OK: obs_events={events_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
