#!/usr/bin/env python3
"""
S29-10 closeout artifact generator.

Goal:
- Freeze S29 Before/After, unresolved risks, and S30 handoff.
- Use S29 SLO readiness as the final decision source.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s29-10"
DEFAULT_READINESS = "docs/evidence/s29-09/slo_readiness_v3_latest.json"
DEFAULT_INDEX = "docs/evidence/s29-08/evidence_trend_index_v4_latest.json"

DEFAULT_UNRESOLVED_RISKS = [
    "provider env 未設定時の SKIP 常態化は運用継続監視が必要。",
    "長時間高負荷時の retry/backoff 最適値は追加検証が必要。",
    "unknown taxonomy の恒常的発生はデータ収集強化が必要。",
]

DEFAULT_HANDOFF = [
    "S30-01: production-connected runbook を運用定着し、失敗系復旧訓練を定例化する。",
    "S30-02: taxonomy pipeline の生成品質指標を追加し、ラベル精度の継続改善を行う。",
    "S30-03: readiness 通知の受信側SLA（ack/再送）を契約化する。",
]

REASON_READINESS_MISSING = "READINESS_MISSING"
REASON_INDEX_MISSING = "INDEX_MISSING"


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


def dedupe_lines(items: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in items:
        text = str(raw or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def derive_unresolved_risks(readiness: Dict[str, Any], index: Dict[str, Any]) -> List[str]:
    risks: List[str] = []
    slo = dict(readiness.get("slo", {}))
    hard = list(slo.get("hard_violations", []))
    soft = list(slo.get("soft_violations", []))
    waived = list(slo.get("waived_hard_violations", []))
    for row in hard:
        metric = str(dict(row).get("metric") or "")
        if metric:
            risks.append(f"{metric} has hard SLO violation and requires immediate remediation.")
    for row in soft:
        metric = str(dict(row).get("metric") or "")
        if metric:
            risks.append(f"{metric} has soft SLO warning and requires ongoing monitoring.")
    for row in waived:
        metric = str(dict(row).get("metric") or "")
        waiver = str(dict(row).get("waiver_code") or "")
        if metric and waiver:
            risks.append(f"{metric} is currently waived ({waiver}); validate exit criteria in production-connected runs.")

    idx_summary = dict(index.get("summary", {}))
    warn_count = int(idx_summary.get("warn_count", 0) or 0)
    failed_count = int(idx_summary.get("failed_count", 0) or 0)
    if failed_count > 0:
        risks.append(f"Evidence trend includes {failed_count} failed phase(s); readiness can regress.")
    if warn_count > 0:
        risks.append(f"Evidence trend includes {warn_count} warning phase(s); continued hardening is required.")

    return dedupe_lines(risks)


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    before_after = dict(payload.get("before_after", {}))
    lines: List[str] = []
    lines.append("# S29-10 Closeout (Latest)")
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
    lines.append(f"- waived_hard_count: `{summary.get('waived_hard_count', 0)}`")
    lines.append("")
    lines.append("## Before / After")
    lines.append("")
    lines.append(f"- before_scope: `{before_after.get('before_scope', '')}`")
    lines.append(f"- after_scope: `{before_after.get('after_scope', '')}`")
    lines.append(f"- before_phases_present: `{before_after.get('before_phases_present', 0)}`")
    lines.append(f"- after_phases_present: `{before_after.get('after_phases_present', 0)}`")
    lines.append(f"- after_failed_warn: `{before_after.get('after_failed_count', 0)}/{before_after.get('after_warn_count', 0)}`")
    lines.append("")
    lines.append("## Unresolved Risks")
    lines.append("")
    for item in list(payload.get("unresolved_risks", [])):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Next Thread Handoff")
    lines.append("")
    for item in list(payload.get("next_thread_handoff", [])):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S29-10 Closeout")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- readiness: {summary.get('readiness', '')}")
    lines.append(f"- blocked_gates: {summary.get('blocked_gates', 0)}")
    lines.append(f"- unresolved_risks: {len(payload.get('unresolved_risks', []))}")
    lines.append(f"- handoff_items: {len(payload.get('next_thread_handoff', []))}")
    lines.append(f"- artifact: docs/evidence/s29-10/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure(
    repo_root: Path,
    out_dir: Path,
    readiness_path: Path,
    index_path: Path,
    reason: str,
    unresolved_risks: List[str],
    handoff_items: List[str],
) -> None:
    payload: Dict[str, Any] = {
        "schema_version": "s29-closeout-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "readiness_json": to_repo_rel(repo_root, readiness_path),
            "index_json": to_repo_rel(repo_root, index_path),
        },
        "before_after": {
            "before_scope": "S28-10 Exit (WARN_ONLY closeout)",
            "after_scope": "S29-10 Exit (production-connected readiness hardening)",
            "before_phases_present": 10,
            "after_phases_present": 0,
            "after_failed_count": 0,
            "after_warn_count": 0,
        },
        "unresolved_risks": list(unresolved_risks),
        "next_thread_handoff": list(handoff_items),
        "summary": {"status": "FAIL", "readiness": "BLOCKED", "blocked_gates": 1, "reason": reason},
        "artifact_names": {"json": "closeout_latest.json", "md": "closeout_latest.md"},
    }
    out_json = out_dir / "closeout_latest.json"
    out_md = out_dir / "closeout_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")


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
    run_dir, meta, events = make_run_context(repo_root, tool="s29-closeout", obs_root=args.obs_root)

    readiness_path = (repo_root / args.readiness_json).resolve()
    index_path = (repo_root / args.index_json).resolve()
    readiness = read_json_if_exists(readiness_path)
    index = read_json_if_exists(index_path)

    manual_risks = list(args.unresolved_risk) if args.unresolved_risk else []
    handoff_items = list(args.handoff) if args.handoff else list(DEFAULT_HANDOFF)

    if not readiness:
        emit("ERROR", f"readiness missing path={readiness_path}", events)
        write_failure(repo_root, out_dir, readiness_path, index_path, REASON_READINESS_MISSING, manual_risks or DEFAULT_UNRESOLVED_RISKS, handoff_items)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason": REASON_READINESS_MISSING})
        return 1
    if not index:
        emit("ERROR", f"index missing path={index_path}", events)
        write_failure(repo_root, out_dir, readiness_path, index_path, REASON_INDEX_MISSING, manual_risks or DEFAULT_UNRESOLVED_RISKS, handoff_items)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason": REASON_INDEX_MISSING})
        return 1

    rsum = dict(readiness.get("summary", {}))
    isum = dict(index.get("summary", {}))

    readiness_state = str(rsum.get("readiness") or "BLOCKED")
    blocked = int(rsum.get("blocked_total", rsum.get("blocked_gates", 0)) or 0)
    if readiness_state in {"READY", "WARN_ONLY"}:
        status = "PASS"
    else:
        status = "FAIL"

    derived_risks = derive_unresolved_risks(readiness, index)
    unresolved_risks = dedupe_lines(manual_risks + derived_risks + ([] if manual_risks else DEFAULT_UNRESOLVED_RISKS))

    before_after = {
        "before_scope": "S28-10 Exit (WARN_ONLY closeout)",
        "after_scope": "S29-10 Exit (production-connected readiness hardening)",
        "before_phases_present": 10,
        "after_phases_present": int(isum.get("present_count", 0) or 0) + 3,
        "after_failed_count": int(isum.get("failed_count", 0) or 0),
        "after_warn_count": int(isum.get("warn_count", 0) or 0),
    }

    payload: Dict[str, Any] = {
        "schema_version": "s29-closeout-v1",
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
            "readiness_reason_code": str(rsum.get("reason_code") or ""),
            "waived_hard_count": int(rsum.get("waived_hard_count", 0) or 0),
            "unresolved_risk_count": len(unresolved_risks),
            "handoff_count": len(handoff_items),
        },
        "artifact_names": {"json": "closeout_latest.json", "md": "closeout_latest.md"},
    }

    if status == "PASS":
        emit("OK", f"closeout status=PASS readiness={readiness_state}", events)
    else:
        emit("ERROR", f"closeout status=FAIL readiness={readiness_state} blocked={blocked}", events)

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
