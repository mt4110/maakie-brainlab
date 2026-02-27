#!/usr/bin/env python3
"""
S25-06 Acceptance Test Wall runner.

Loads acceptance cases from docs/ops/S25-06_ACCEPTANCE_CASES.json,
runs them deterministically, and writes latest evidence for PR body.
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


DEFAULT_CASES_FILE = "docs/ops/S25-06_ACCEPTANCE_CASES.json"
DEFAULT_OUT_DIR = "docs/evidence/s25-06"
DEFAULT_TIMEOUT_SEC = 600

REASON_RC_NONZERO = "RC_NONZERO"
REASON_PASS_REGEX_MISSING = "PASS_REGEX_MISSING"
REASON_CASE_INVALID = "CASE_INVALID"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    rel_posix = rel.as_posix()
    if ".." in Path(rel_posix).parts:
        return ""
    return rel_posix


def load_cases(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return "", []
    schema = str(obj.get("schema_version") or "")
    items = obj.get("cases")
    if not isinstance(items, list):
        return schema, []
    out: List[Dict[str, Any]] = []
    for raw in items:
        if isinstance(raw, dict):
            out.append(raw)
    return schema, out


def validate_case(case: Dict[str, Any]) -> Tuple[bool, str]:
    cid = str(case.get("id") or "").strip()
    command = str(case.get("command") or "").strip()
    if not cid:
        return False, "missing id"
    if not command:
        return False, "missing command"
    return True, ""


def run_case_command(cmd: str, repo_root: Path, timeout_sec: int) -> Tuple[int, str]:
    try:
        cp = subprocess.run(
            ["bash", "-lc", cmd],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        output = (cp.stdout or "") + (cp.stderr or "")
        return cp.returncode, output
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "")
        return 124, out + f"\nERROR: timeout after {timeout_sec}s\n"


def evaluate_case(case: Dict[str, Any], rc: int, output: str) -> Tuple[str, str]:
    must_pass = bool(case.get("must_pass", True))
    pass_regex = str(case.get("pass_regex") or "").strip()

    if must_pass and rc != 0:
        return "FAIL", REASON_RC_NONZERO
    if pass_regex:
        if re.search(pass_regex, output, flags=re.M) is None:
            return "FAIL", REASON_PASS_REGEX_MISSING
    return "PASS", ""


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# S25-06 Acceptance Test Wall (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload['captured_at_utc']}`")
    lines.append(f"- Branch: `{payload['git']['branch']}`")
    lines.append(f"- HeadSHA: `{payload['git']['head']}`")
    lines.append(f"- CasesFile: `{payload['cases_file']}`")
    lines.append("")
    lines.append("## Acceptance Metrics")
    lines.append("")
    lines.append(f"- Cases: `{summary['passed_cases']}/{summary['total_cases']}` passed")
    lines.append(f"- Speed(total): `{summary['total_duration_sec']} sec`")
    lines.append(f"- Failure taxonomy entries: `{len(summary['failure_counts'])}`")
    lines.append("")
    lines.append("## Case Results")
    lines.append("")
    for item in payload["cases"]:
        reason = item.get("reason_code") or "-"
        lines.append(
            f"- `{item['status']}` `{item['case_id']}` `{item['duration_sec']}s` "
            f"`{item['title']}` reason=`{reason}`"
        )
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-06 Acceptance Test Wall")
    lines.append(f"- acceptance: {summary['passed_cases']}/{summary['total_cases']} passed")
    lines.append(f"- speed: total {summary['total_duration_sec']} sec")
    if summary["failure_counts"]:
        lines.append(f"- failure_taxonomy: {summary['failure_counts']}")
    else:
        lines.append("- failure_taxonomy: none")
    lines.append(f"- artifact: docs/evidence/s25-06/{payload['artifact_names']['json']}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-file", default=DEFAULT_CASES_FILE)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    cases_path = (repo_root / args.cases_file).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="acceptance-wall", obs_root=args.obs_root)

    if not cases_path.exists():
        emit("ERROR", f"cases file missing path={cases_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1})
        return

    schema, cases = load_cases(cases_path)
    emit("OK", f"cases_file={cases_path}", events)
    emit("OK", f"cases_loaded={len(cases)} schema={schema}", events)

    results: List[Dict[str, Any]] = []
    failure_counts: Dict[str, int] = {}
    stop = 0
    for i, case in enumerate(cases, start=1):
        valid, reason = validate_case(case)
        cid = str(case.get("id") or f"case-{i}")
        title = str(case.get("title") or cid)
        cmd = str(case.get("command") or "")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", cid).strip("_").lower() or f"case_{i}"
        log_path = run_dir / f"{i:02d}_{slug}.log"

        if not valid:
            stop = 1
            status = "FAIL"
            reason_code = REASON_CASE_INVALID
            output = f"ERROR: invalid case {cid}: {reason}\n"
            rc = 2
            emit("ERROR", f"case[{cid}] invalid reason={reason}", events)
        else:
            emit("OK", f"case[{cid}] run={cmd}", events)
            t0 = utc_now()
            rc, output = run_case_command(cmd, repo_root=repo_root, timeout_sec=max(1, int(args.timeout_sec)))
            t1 = utc_now()
            status, reason_code = evaluate_case(case, rc, output)
            duration_sec = round((t1 - t0).total_seconds(), 3)
            log_path.write_text(output, encoding="utf-8")
            if status == "PASS":
                emit("OK", f"case[{cid}] PASS rc={rc} duration={duration_sec}s", events)
            else:
                stop = 1
                emit("ERROR", f"case[{cid}] FAIL rc={rc} reason={reason_code} duration={duration_sec}s", events)
            if status == "FAIL" and reason_code:
                failure_counts[reason_code] = failure_counts.get(reason_code, 0) + 1
            results.append(
                {
                    "case_id": cid,
                    "title": title,
                    "category": str(case.get("category") or ""),
                    "status": status,
                    "reason_code": reason_code,
                    "command": cmd,
                    "rc": rc,
                    "duration_sec": duration_sec,
                    "log_path": to_repo_rel(repo_root, log_path),
                }
            )
            continue

        log_path.write_text(output, encoding="utf-8")
        failure_counts[reason_code] = failure_counts.get(reason_code, 0) + 1
        results.append(
            {
                "case_id": cid,
                "title": title,
                "category": str(case.get("category") or ""),
                "status": status,
                "reason_code": reason_code,
                "command": cmd,
                "rc": rc,
                "duration_sec": 0.0,
                "log_path": to_repo_rel(repo_root, log_path),
            }
        )

    total_sec = round(sum(float(x["duration_sec"]) for x in results), 3)
    passed = sum(1 for x in results if x["status"] == "PASS")

    payload: Dict[str, Any] = {
        "schema_version": "s25-acceptance-wall-v1",
        "captured_at_utc": utc_now().isoformat(),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "cases_file": to_repo_rel(repo_root, cases_path),
        "summary": {
            "total_cases": len(results),
            "passed_cases": passed,
            "failed_cases": len(results) - passed,
            "total_duration_sec": total_sec,
            "failure_counts": failure_counts,
        },
        "cases": results,
        "artifact_names": {
            "json": "acceptance_wall_latest.json",
            "md": "acceptance_wall_latest.md",
            "run_dir": to_repo_rel(repo_root, run_dir),
        },
        "stop": stop,
    }

    out_json = out_dir / "acceptance_wall_latest.json"
    out_md = out_dir / "acceptance_wall_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"acceptance_json={out_json}", events)
    emit("OK", f"acceptance_md={out_md}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    if stop == 0:
        emit("OK", "acceptance_wall completed", events)
    else:
        emit("WARN", "acceptance_wall completed with failures", events)

    events_path = write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "acceptance_json": to_repo_rel(repo_root, out_json),
            "acceptance_md": to_repo_rel(repo_root, out_md),
            "stop": stop,
            "cases_total": len(results),
        },
    )
    print(f"OK: obs_events={events_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
