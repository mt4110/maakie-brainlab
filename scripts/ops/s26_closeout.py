#!/usr/bin/env python3
"""
S26-10 closeout artifact generator.

Goal:
- Freeze Before/After, unresolved risks, and S27 handoff in one artifact.
- Use S26 release-readiness output as the final gate source.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s26-10"
DEFAULT_READINESS = "docs/evidence/s26-09/release_readiness_latest.json"
DEFAULT_INDEX = "docs/evidence/s26-08/evidence_index_latest.json"

DEFAULT_UNRESOLVED_RISKS = [
    "provider env が未設定の場合、canary は SKIP となり実接続品質は未検証のまま残る。",
    "長時間/高負荷での retry/backoff 妥当性は別スレッドで継続検証が必要。",
]

DEFAULT_HANDOFF = [
    "S27-01: provider 実接続 canary を定常運用化し、SKIP率を継続監視する。",
    "S27-02: medium eval wall を運用データで拡張し、失敗 taxonomy の粒度を上げる。",
    "S27-03: release-readiness を CI 定期実行へ昇格する。",
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


def phase_to_index(phase: str) -> int:
    text = str(phase or "").strip().upper()
    if not text.startswith("S26-"):
        return -1
    tail = text.split("-", 1)[1]
    if not tail.isdigit():
        return -1
    return int(tail)


def count_present_until(phases: List[Dict[str, Any]], max_index: int) -> int:
    total = 0
    for row in phases:
        idx = phase_to_index(str(row.get("phase", "")))
        if idx < 0 or idx > max_index:
            continue
        if bool(row.get("present")):
            total += 1
    return total


def count_present_between(phases: List[Dict[str, Any]], min_index: int, max_index: int) -> int:
    total = 0
    for row in phases:
        idx = phase_to_index(str(row.get("phase", "")))
        if idx < min_index or idx > max_index:
            continue
        if bool(row.get("present")):
            total += 1
    return total


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    before_after = payload["before_after"]
    lines: List[str] = []
    lines.append("# S26-10 Closeout (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- readiness: `{summary.get('readiness', '')}`")
    lines.append(f"- blocked_gates: `{summary.get('blocked_gates', 0)}`")
    lines.append("")
    lines.append("## Before / After")
    lines.append("")
    lines.append(f"- before_scope: `{before_after.get('before_scope', '')}`")
    lines.append(f"- after_scope: `{before_after.get('after_scope', '')}`")
    lines.append(f"- before_phases_present: `{before_after.get('before_phases_present', 0)}`")
    lines.append(f"- after_phases_present: `{before_after.get('after_phases_present', 0)}`")
    lines.append(f"- after_scope_detail: `{before_after.get('after_scope_detail', '')}`")
    lines.append(f"- after_failed_warn: `{before_after.get('after_failed_count', 0)}/{before_after.get('after_warn_count', 0)}`")
    lines.append("")
    lines.append("## Unresolved Risks")
    lines.append("")
    for item in payload.get("unresolved_risks", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Next Thread Handoff")
    lines.append("")
    for item in payload.get("next_thread_handoff", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-10 Closeout")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- readiness: {summary.get('readiness', '')}")
    lines.append(f"- blocked_gates: {summary.get('blocked_gates', 0)}")
    lines.append(f"- unresolved_risks: {len(payload.get('unresolved_risks', []))}")
    lines.append(f"- handoff_items: {len(payload.get('next_thread_handoff', []))}")
    lines.append(f"- artifact: docs/evidence/s26-10/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--readiness-json", default=DEFAULT_READINESS)
    parser.add_argument("--index-json", default=DEFAULT_INDEX)
    parser.add_argument("--unresolved-risk", action="append", default=[])
    parser.add_argument("--handoff", action="append", default=[])
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-closeout", obs_root=args.obs_root)

    readiness_path = (repo_root / args.readiness_json).resolve()
    index_path = (repo_root / args.index_json).resolve()
    readiness = read_json_if_exists(readiness_path)
    index = read_json_if_exists(index_path)

    if not readiness:
        emit("ERROR", f"readiness missing path={readiness_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason": "READINESS_MISSING"})
        return 1
    if not index:
        emit("ERROR", f"evidence index missing path={index_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason": "INDEX_MISSING"})
        return 1

    readiness_summary = dict(readiness.get("summary", {}))
    index_summary = dict(index.get("summary", {}))
    phases = list(index.get("phases", [])) if isinstance(index.get("phases"), list) else []

    before_present = count_present_until(phases, max_index=4)
    after_present_core = count_present_between(phases, min_index=1, max_index=7)
    after_present = after_present_core
    # S26-08/09/10 are not inside index phases list; add explicitly.
    after_present += 1  # S26-08 index itself exists by this point
    if bool(readiness):
        after_present += 1  # S26-09 readiness artifact loaded
    after_present += 1  # S26-10 closeout artifact generation in progress

    unresolved_risks = list(args.unresolved_risk) if args.unresolved_risk else list(DEFAULT_UNRESOLVED_RISKS)
    handoff_items = list(args.handoff) if args.handoff else list(DEFAULT_HANDOFF)

    readiness_state = str(readiness_summary.get("readiness") or "BLOCKED")
    blocked = int(readiness_summary.get("blocked_gates", 0))
    status = "PASS" if readiness_state == "READY" else "FAIL"

    before_after = {
        "before_scope": "S26-04 Exit (core orchestration only)",
        "after_scope": "S26-10 Exit (regression/acceptance/reliability/readiness/closeout)",
        "after_scope_detail": "S26-01..07(indexed) + S26-08(index) + S26-09(readiness) + S26-10(closeout)",
        "before_phases_present": before_present,
        "after_phases_present": after_present,
        "after_failed_count": int(index_summary.get("failed_count", 0)),
        "after_warn_count": int(index_summary.get("warn_count", 0)),
    }

    payload: Dict[str, Any] = {
        "schema_version": "s26-closeout-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "readiness_json": to_repo_rel(repo_root, readiness_path),
            "index_json": to_repo_rel(repo_root, index_path),
        },
        "before_after": before_after,
        "unresolved_risks": unresolved_risks,
        "next_thread_handoff": handoff_items,
        "summary": {
            "status": status,
            "readiness": readiness_state,
            "blocked_gates": blocked,
        },
        "artifact_names": {
            "json": "closeout_latest.json",
            "md": "closeout_latest.md",
        },
    }

    if status == "PASS":
        emit("OK", f"closeout status=PASS readiness={readiness_state}", events)
    else:
        emit("ERROR", f"closeout status=FAIL readiness={readiness_state} blocked_gates={blocked}", events)

    out_json = out_dir / "closeout_latest.json"
    out_md = out_dir / "closeout_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "readiness": readiness_state})
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
