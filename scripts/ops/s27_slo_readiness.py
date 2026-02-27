#!/usr/bin/env python3
"""
S27-09 SLO-based readiness decision.

Goal:
- Aggregate S27 evidence with soft/hard SLO thresholds.
- Output READY / WARN_ONLY / BLOCKED with explicit reasons.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s27-09"

ARTIFACTS = {
    "S27-01": "docs/evidence/s27-01/provider_canary_ops_latest.json",
    "S27-02": "docs/evidence/s27-02/medium_eval_wall_v2_latest.json",
    "S27-03": "docs/evidence/s27-03/release_readiness_schedule_latest.json",
    "S27-04": "docs/evidence/s27-04/incident_triage_pack_latest.json",
    "S27-05": "docs/evidence/s27-05/policy_drift_guard_latest.json",
    "S27-06": "docs/evidence/s27-06/reliability_soak_latest.json",
    "S27-07": "docs/evidence/s27-07/acceptance_wall_v2_latest.json",
    "S27-08": "docs/evidence/s27-08/evidence_trend_index_latest.json",
}

REASON_GATES_BLOCKED = "GATES_BLOCKED"
REASON_HARD_SLO_VIOLATION = "HARD_SLO_VIOLATION"
REASON_SOFT_SLO_WARN = "SOFT_SLO_WARN"


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


def infer_status(doc: Dict[str, Any]) -> str:
    summary = dict(doc.get("summary", {}))
    status = str(summary.get("status") or "").upper().strip()
    if status in {"PASS", "WARN", "FAIL", "SKIP", "MISSING"}:
        return status
    if status in {"OK", "SUCCESS"}:
        return "PASS"
    if status in {"ERROR"}:
        return "FAIL"
    readiness = str(summary.get("readiness") or "").upper().strip()
    if readiness == "READY":
        return "PASS"
    if readiness == "WARN_ONLY":
        return "WARN"
    if readiness == "BLOCKED":
        return "FAIL"
    return "MISSING"


def compute_blocked_total(blocked_gates: int, hard_violations: List[Dict[str, Any]]) -> int:
    return int(blocked_gates) + len(list(hard_violations))


def build_gate_rows(docs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for phase in ["S27-01", "S27-02", "S27-03", "S27-04", "S27-05", "S27-06", "S27-07", "S27-08"]:
        doc = docs.get(phase, {})
        st = infer_status(doc) if doc else "MISSING"
        rows.append(
            {
                "phase": phase,
                "gate": "status must not be FAIL/MISSING",
                "actual": st,
                "passed": st not in {"FAIL", "MISSING"},
            }
        )
    return rows


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def evaluate_slo(
    *,
    skip_rate: float,
    unknown_ratio: float,
    acceptance_pass_rate: float,
    skip_soft: float,
    skip_hard: float,
    unknown_soft: float,
    unknown_hard: float,
    acceptance_soft: float,
    acceptance_hard: float,
) -> Dict[str, List[Dict[str, Any]]]:
    hard: List[Dict[str, Any]] = []
    soft: List[Dict[str, Any]] = []

    if skip_rate > skip_hard:
        hard.append({"metric": "skip_rate", "value": skip_rate, "threshold": skip_hard, "rule": "value <= hard"})
    elif skip_rate > skip_soft:
        soft.append({"metric": "skip_rate", "value": skip_rate, "threshold": skip_soft, "rule": "value <= soft"})

    if unknown_ratio > unknown_hard:
        hard.append({"metric": "unknown_ratio", "value": unknown_ratio, "threshold": unknown_hard, "rule": "value <= hard"})
    elif unknown_ratio > unknown_soft:
        soft.append({"metric": "unknown_ratio", "value": unknown_ratio, "threshold": unknown_soft, "rule": "value <= soft"})

    if acceptance_pass_rate < acceptance_hard:
        hard.append(
            {
                "metric": "acceptance_pass_rate",
                "value": acceptance_pass_rate,
                "threshold": acceptance_hard,
                "rule": "value >= hard",
            }
        )
    elif acceptance_pass_rate < acceptance_soft:
        soft.append(
            {
                "metric": "acceptance_pass_rate",
                "value": acceptance_pass_rate,
                "threshold": acceptance_soft,
                "rule": "value >= soft",
            }
        )

    return {"hard": hard, "soft": soft}


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    metrics = dict(payload.get("metrics", {}))
    lines: List[str] = []
    lines.append("# S27-09 SLO Readiness (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- readiness: `{summary.get('readiness', '')}`")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- passed_gates: `{summary.get('passed_gates', 0)}/{summary.get('total_gates', 0)}`")
    lines.append(f"- hard_soft: `{summary.get('hard_block_count', 0)}/{summary.get('soft_warn_count', 0)}`")
    lines.append("")
    lines.append("## SLO Metrics")
    lines.append("")
    lines.append(f"- skip_rate: `{metrics.get('skip_rate', 0.0)}`")
    lines.append(f"- unknown_ratio: `{metrics.get('unknown_ratio', 0.0)}`")
    lines.append(f"- acceptance_pass_rate: `{metrics.get('acceptance_pass_rate', 0.0)}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S27-09 SLO Readiness")
    lines.append(f"- readiness: {summary.get('readiness', '')}")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- passed_gates: {summary.get('passed_gates', 0)}/{summary.get('total_gates', 0)}")
    lines.append(f"- hard_soft: {summary.get('hard_block_count', 0)}/{summary.get('soft_warn_count', 0)}")
    lines.append(f"- metrics(skip/unknown/acc): {metrics.get('skip_rate', 0.0)}/{metrics.get('unknown_ratio', 0.0)}/{metrics.get('acceptance_pass_rate', 0.0)}")
    lines.append(f"- artifact: docs/evidence/s27-09/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--skip-rate-soft", type=float, default=0.40)
    parser.add_argument("--skip-rate-hard", type=float, default=1.00)
    parser.add_argument("--unknown-ratio-soft", type=float, default=0.20)
    parser.add_argument("--unknown-ratio-hard", type=float, default=0.40)
    parser.add_argument("--acceptance-pass-rate-soft", type=float, default=0.90)
    parser.add_argument("--acceptance-pass-rate-hard", type=float, default=0.75)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s27-slo-readiness", obs_root=args.obs_root)

    current_head = git_out(repo_root, ["rev-parse", "HEAD"])
    docs: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []
    stale: List[str] = []

    for phase, rel in ARTIFACTS.items():
        path = (repo_root / rel).resolve()
        doc = read_json_if_exists(path)
        if not doc:
            missing.append(phase)
            emit("ERROR", f"missing phase={phase} path={path}", events)
            docs[phase] = {}
            continue
        if is_stale_artifact(doc, current_head):
            stale.append(phase)
            emit("ERROR", f"stale phase={phase}", events)
            docs[phase] = {}
            continue
        docs[phase] = doc
        emit("OK", f"loaded phase={phase}", events)

    gates = build_gate_rows(docs)
    for row in gates:
        level = "OK" if row["passed"] else "ERROR"
        emit(level, f"gate={row['phase']} passed={row['passed']} actual={row['actual']}", events)

    passed_gates = sum(1 for g in gates if g["passed"])
    blocked_gates = len(gates) - passed_gates

    d01 = docs.get("S27-01", {})
    d02 = docs.get("S27-02", {})
    d07 = docs.get("S27-07", {})
    skip_rate = to_float(dict(d01.get("trend", {})).get("skip_rate", 0.0), 0.0)
    unknown_ratio = to_float(dict(d02.get("taxonomy", {})).get("unknown_ratio", 0.0), 0.0)
    acc_sum = dict(d07.get("summary", {}))
    acc_total = to_int(acc_sum.get("total_cases", 0), 0)
    acc_passed = to_int(acc_sum.get("passed_cases", 0), 0)
    acceptance_pass_rate = 0.0 if acc_total <= 0 else round(acc_passed / float(acc_total), 4)

    slo_eval = evaluate_slo(
        skip_rate=skip_rate,
        unknown_ratio=unknown_ratio,
        acceptance_pass_rate=acceptance_pass_rate,
        skip_soft=float(args.skip_rate_soft),
        skip_hard=float(args.skip_rate_hard),
        unknown_soft=float(args.unknown_ratio_soft),
        unknown_hard=float(args.unknown_ratio_hard),
        acceptance_soft=float(args.acceptance_pass_rate_soft),
        acceptance_hard=float(args.acceptance_pass_rate_hard),
    )

    hard = list(slo_eval.get("hard", []))
    soft = list(slo_eval.get("soft", []))

    readiness = "READY"
    status = "PASS"
    reason_code = ""
    if missing or stale or blocked_gates > 0:
        readiness = "BLOCKED"
        status = "FAIL"
        reason_code = REASON_GATES_BLOCKED
    elif hard:
        readiness = "BLOCKED"
        status = "FAIL"
        reason_code = REASON_HARD_SLO_VIOLATION
    elif soft:
        readiness = "WARN_ONLY"
        status = "WARN"
        reason_code = REASON_SOFT_SLO_WARN

    if status == "FAIL":
        emit("ERROR", f"slo readiness=BLOCKED reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"slo readiness=WARN_ONLY reason={reason_code}", events)
    else:
        emit("OK", "slo readiness=READY", events)

    payload: Dict[str, Any] = {
        "schema_version": "s27-slo-readiness-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": current_head},
        "inputs": ARTIFACTS,
        "missing_phases": missing,
        "stale_phases": stale,
        "gates": gates,
        "metrics": {
            "skip_rate": skip_rate,
            "unknown_ratio": unknown_ratio,
            "acceptance_pass_rate": acceptance_pass_rate,
            "acceptance_passed": acc_passed,
            "acceptance_total": acc_total,
        },
        "slo": {
            "hard_violations": hard,
            "soft_violations": soft,
            "thresholds": {
                "skip_rate_soft": float(args.skip_rate_soft),
                "skip_rate_hard": float(args.skip_rate_hard),
                "unknown_ratio_soft": float(args.unknown_ratio_soft),
                "unknown_ratio_hard": float(args.unknown_ratio_hard),
                "acceptance_pass_rate_soft": float(args.acceptance_pass_rate_soft),
                "acceptance_pass_rate_hard": float(args.acceptance_pass_rate_hard),
            },
        },
        "summary": {
            "readiness": readiness,
            "status": status,
            "reason_code": reason_code,
            "total_gates": len(gates),
            "passed_gates": passed_gates,
            "blocked_gates": blocked_gates,
            "blocked_total": compute_blocked_total(blocked_gates, hard),
            "hard_block_count": len(hard),
            "soft_warn_count": len(soft),
            "missing_count": len(missing),
            "stale_count": len(stale),
        },
        "artifact_names": {"json": "slo_readiness_latest.json", "md": "slo_readiness_latest.md"},
    }

    out_json = out_dir / "slo_readiness_latest.json"
    out_md = out_dir / "slo_readiness_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"readiness": readiness, "status": status, "reason_code": reason_code})
    return 0 if readiness != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
