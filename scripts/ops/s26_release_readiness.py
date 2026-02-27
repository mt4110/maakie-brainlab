#!/usr/bin/env python3
"""
S26-09 release readiness gate.

Goal:
- Aggregate S26 evidence and produce one readiness decision.
- Keep rollback command visible for immediate recovery.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s26-09"

ARTIFACTS = {
    "S26-01": "docs/evidence/s26-01/provider_canary_latest.json",
    "S26-02": "docs/evidence/s26-02/medium_eval_wall_latest.json",
    "S26-03": "docs/evidence/s26-03/rollback_artifact_latest.json",
    "S26-04": "docs/evidence/s26-04/orchestration_core_latest.json",
    "S26-05": "docs/evidence/s26-05/regression_safety_latest.json",
    "S26-06": "docs/evidence/s26-06/acceptance_wall_latest.json",
    "S26-07": "docs/evidence/s26-07/reliability_report_latest.json",
    "S26-08": "docs/evidence/s26-08/evidence_index_latest.json",
}


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


def is_stale_artifact(doc: Dict[str, Any], current_head: str) -> bool:
    if not current_head:
        return False
    doc_head = str(dict(doc.get("git", {})).get("head") or "")
    if not doc_head:
        return False
    return doc_head != current_head


def to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def build_gate_rows(docs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    s26_01 = docs.get("S26-01", {})
    s26_01_status = str(dict(s26_01.get("summary", {})).get("status") or "")
    rows.append({"phase": "S26-01", "gate": "canary status PASS/SKIP", "actual": s26_01_status, "passed": s26_01_status in {"PASS", "SKIP"}})

    s26_02 = docs.get("S26-02", {})
    s26_02_status = str(dict(s26_02.get("summary", {})).get("status") or "")
    rows.append({"phase": "S26-02", "gate": "medium eval status PASS", "actual": s26_02_status, "passed": s26_02_status == "PASS"})

    s26_03 = docs.get("S26-03", {})
    s26_03_status = str(dict(s26_03.get("summary", {})).get("status") or "")
    rows.append({"phase": "S26-03", "gate": "rollback artifact status PASS", "actual": s26_03_status, "passed": s26_03_status == "PASS"})

    s26_04 = docs.get("S26-04", {})
    s26_04_status = str(dict(s26_04.get("summary", {})).get("status") or "")
    rows.append({"phase": "S26-04", "gate": "orchestration status PASS", "actual": s26_04_status, "passed": s26_04_status == "PASS"})

    s26_05 = docs.get("S26-05", {})
    s26_05_stop = to_int(s26_05.get("stop", 1), 1) if isinstance(s26_05, dict) else 1
    rows.append({"phase": "S26-05", "gate": "regression stop flag == 0", "actual": s26_05_stop, "passed": s26_05_stop == 0})

    s26_06 = docs.get("S26-06", {})
    s26_06_failed = to_int(dict(s26_06.get("summary", {})).get("failed_cases", 1), 1)
    rows.append({"phase": "S26-06", "gate": "acceptance failed_cases == 0", "actual": s26_06_failed, "passed": s26_06_failed == 0})

    s26_07 = docs.get("S26-07", {})
    s26_07_status = str(dict(s26_07.get("summary", {})).get("status") or "")
    rows.append({"phase": "S26-07", "gate": "reliability status PASS/WARN", "actual": s26_07_status, "passed": s26_07_status in {"PASS", "WARN"}})

    s26_08 = docs.get("S26-08", {})
    s26_08_status = str(dict(s26_08.get("summary", {})).get("status") or "")
    rows.append({"phase": "S26-08", "gate": "evidence index status PASS/WARN", "actual": s26_08_status, "passed": s26_08_status in {"PASS", "WARN"}})

    return rows


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# S26-09 Release Readiness (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- readiness: `{summary.get('readiness', '')}`")
    lines.append(f"- passed_gates: `{summary.get('passed_gates', 0)}/{summary.get('total_gates', 0)}`")
    lines.append(f"- blocked_gates: `{summary.get('blocked_gates', 0)}`")
    lines.append(f"- stale_phases: `{summary.get('stale_count', 0)}`")
    lines.append(f"- rollback_command: `{payload.get('rollback_command', '')}`")
    lines.append("")
    lines.append("## Gate Results")
    lines.append("")
    for row in payload.get("gates", []):
        mark = "PASS" if row.get("passed") else "FAIL"
        lines.append(f"- {mark}: `{row.get('phase')}` {row.get('gate')} (actual=`{row.get('actual')}`)")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-09 Release Readiness")
    lines.append(f"- readiness: {summary.get('readiness', '')}")
    lines.append(f"- passed_gates: {summary.get('passed_gates', 0)}/{summary.get('total_gates', 0)}")
    lines.append(f"- blocked_gates: {summary.get('blocked_gates', 0)}")
    lines.append(f"- stale_count: {summary.get('stale_count', 0)}")
    lines.append(f"- rollback_command: {payload.get('rollback_command', '')}")
    lines.append(f"- artifact: docs/evidence/s26-09/{payload.get('artifact_names', {}).get('json', '')}")
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
    run_dir, meta, events = make_run_context(repo_root, tool="s26-release-readiness", obs_root=args.obs_root)

    docs: Dict[str, Dict[str, Any]] = {}
    inputs: Dict[str, str] = {}
    missing: List[str] = []
    stale: List[str] = []
    current_head = git_out(repo_root, ["rev-parse", "HEAD"])

    for phase, rel in ARTIFACTS.items():
        path = (repo_root / rel).resolve()
        inputs[phase] = rel
        doc = read_json_if_exists(path)
        docs[phase] = doc
        if not doc:
            missing.append(phase)
            emit("ERROR", f"missing phase={phase} path={path}", events)
        else:
            if is_stale_artifact(doc, current_head):
                doc_head = str(dict(doc.get("git", {})).get("head") or "")
                stale.append(phase)
                docs[phase] = {}
                emit("ERROR", f"stale phase={phase} artifact_head={doc_head} current_head={current_head}", events)
            else:
                emit("OK", f"loaded phase={phase} path={rel}", events)

    gates = build_gate_rows(docs)
    for row in gates:
        if row["passed"]:
            emit("OK", f"gate={row['phase']} PASS actual={row['actual']}", events)
        else:
            emit("ERROR", f"gate={row['phase']} FAIL actual={row['actual']}", events)

    passed_gates = sum(1 for row in gates if bool(row.get("passed")))
    blocked_gates = len(gates) - passed_gates
    readiness = "READY" if blocked_gates == 0 and not missing and not stale else "BLOCKED"

    rollback_command = str(docs.get("S26-03", {}).get("rollback_command") or "")

    payload: Dict[str, Any] = {
        "schema_version": "s26-release-readiness-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": inputs,
        "missing_phases": missing,
        "stale_phases": stale,
        "gates": gates,
        "rollback_command": rollback_command,
        "summary": {
            "readiness": readiness,
            "total_gates": len(gates),
            "passed_gates": passed_gates,
            "blocked_gates": blocked_gates,
            "stale_count": len(stale),
        },
        "artifact_names": {
            "json": "release_readiness_latest.json",
            "md": "release_readiness_latest.md",
        },
    }

    out_json = out_dir / "release_readiness_latest.json"
    out_md = out_dir / "release_readiness_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"readiness": readiness, "blocked_gates": blocked_gates})
    return 0 if readiness == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
