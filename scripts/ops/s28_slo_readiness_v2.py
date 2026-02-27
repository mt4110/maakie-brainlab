#!/usr/bin/env python3
"""
S28-09 SLO-based readiness decision v2.

Goal:
- Aggregate S28 phase artifacts into READY / WARN_ONLY / BLOCKED.
- Add notification delivery signal to SLO evaluation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s28-09"

ARTIFACTS = {
    "S28-01": "docs/evidence/s28-01/provider_canary_recovery_latest.json",
    "S28-02": "docs/evidence/s28-02/taxonomy_feedback_loop_latest.json",
    "S28-03": "docs/evidence/s28-03/readiness_notify_latest.json",
    "S28-04": "docs/evidence/s28-04/incident_triage_pack_v2_latest.json",
    "S28-05": "docs/evidence/s28-05/policy_drift_guard_v2_latest.json",
    "S28-06": "docs/evidence/s28-06/reliability_soak_v2_latest.json",
    "S28-07": "docs/evidence/s28-07/acceptance_wall_v3_latest.json",
    "S28-08": "docs/evidence/s28-08/evidence_trend_index_v3_latest.json",
}

REASON_GATES_BLOCKED = "GATES_BLOCKED"
REASON_HARD_SLO_VIOLATION = "HARD_SLO_VIOLATION"
REASON_SOFT_SLO_WARN = "SOFT_SLO_WARN"

WAIVER_SKIP_RATE_ENV_GAP = "SKIP_RATE_ENV_GAP"
WAIVER_NOTIFY_NOT_ATTEMPTED = "NOTIFY_NOT_ATTEMPTED"
WAIVER_RELIABILITY_ENV_GAP = "RELIABILITY_ENV_GAP"
WAIVER_UNKNOWN_RATIO_WITH_ACTIONS = "UNKNOWN_RATIO_WITH_ACTIONS"


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


def head_relation(repo_root: Path, artifact_head: str, current_head: str) -> str:
    art = str(artifact_head or "").strip()
    cur = str(current_head or "").strip()
    if not art or not cur:
        return "unknown"
    if art == cur:
        return "exact"
    try:
        cp = subprocess.run(
            ["git", "merge-base", "--is-ancestor", art, cur],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return "unknown"
    if int(cp.returncode) == 0:
        return "ancestor"
    return "diverged"


def is_stale_artifact(doc: Dict[str, Any], current_head: str, repo_root: Path) -> bool:
    if not current_head:
        return False
    doc_head = str(dict(doc.get("git", {})).get("head") or "")
    if not doc_head:
        return False
    relation = head_relation(repo_root, doc_head, current_head)
    return relation in {"diverged", "unknown"}


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


def build_gate_rows(docs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for phase in ["S28-01", "S28-02", "S28-03", "S28-04", "S28-05", "S28-06", "S28-07", "S28-08"]:
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


def compute_notify_delivery_rate(*, notify_sent: bool, notify_attempt_count: int, notify_attempted: bool) -> float:
    attempts = max(0, int(notify_attempt_count))
    if attempts <= 0:
        if notify_attempted:
            return 1.0 if notify_sent else 0.0
        return 0.0
    success = 1 if notify_sent else 0
    return round(success / float(attempts), 4)


def evaluate_slo(
    *,
    skip_rate: float,
    unknown_ratio: float,
    acceptance_pass_rate: float,
    notify_delivery_rate: float,
    reliability_total_runs: int,
    skip_soft: float,
    skip_hard: float,
    unknown_soft: float,
    unknown_hard: float,
    acceptance_soft: float,
    acceptance_hard: float,
    notify_soft: float,
    notify_hard: float,
    reliability_runs_soft_min: int,
    reliability_runs_hard_min: int,
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
        hard.append({"metric": "acceptance_pass_rate", "value": acceptance_pass_rate, "threshold": acceptance_hard, "rule": "value >= hard"})
    elif acceptance_pass_rate < acceptance_soft:
        soft.append({"metric": "acceptance_pass_rate", "value": acceptance_pass_rate, "threshold": acceptance_soft, "rule": "value >= soft"})

    if notify_delivery_rate < notify_hard:
        hard.append({"metric": "notify_delivery_rate", "value": notify_delivery_rate, "threshold": notify_hard, "rule": "value >= hard"})
    elif notify_delivery_rate < notify_soft:
        soft.append({"metric": "notify_delivery_rate", "value": notify_delivery_rate, "threshold": notify_soft, "rule": "value >= soft"})

    if reliability_total_runs < reliability_runs_hard_min:
        hard.append(
            {
                "metric": "reliability_total_runs",
                "value": reliability_total_runs,
                "threshold": reliability_runs_hard_min,
                "rule": "value >= hard",
            }
        )
    elif reliability_total_runs < reliability_runs_soft_min:
        soft.append(
            {
                "metric": "reliability_total_runs",
                "value": reliability_total_runs,
                "threshold": reliability_runs_soft_min,
                "rule": "value >= soft",
            }
        )

    return {"hard": hard, "soft": soft}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return bool(value)


def build_waiver_context(
    *,
    d01: Dict[str, Any],
    d02: Dict[str, Any],
    d03: Dict[str, Any],
    d06: Dict[str, Any],
    env_gap_waiver_min_rate: float,
) -> Dict[str, Any]:
    trend = dict(d01.get("trend", {}))
    d01_summary = dict(d01.get("summary", {}))
    d02_metrics = dict(d02.get("metrics", {}))
    d03_summary = dict(d03.get("summary", {}))
    d03_notify = dict(d03.get("notification", {}))
    d06_summary = dict(d06.get("summary", {}))
    d06_metrics = dict(d06.get("metrics", {}))

    provider_env_gap = (
        str(trend.get("dominant_skip_cause") or "") == "env"
        and to_float(trend.get("env_skip_rate", 0.0), 0.0) >= float(env_gap_waiver_min_rate)
    ) or _to_bool(d01_summary.get("env_gap_detected"))

    notify_reason = str(d03_summary.get("reason_code") or "")
    notify_attempted = _to_bool(d03_notify.get("attempted"))
    notify_not_attempted = (not notify_attempted) and notify_reason in {"NOTIFY_DRY_RUN", "WEBHOOK_NOT_CONFIGURED"}
    notify_delivery_state = str(d03_notify.get("delivery_state") or "")
    if notify_delivery_state == "NOT_ATTEMPTED":
        notify_not_attempted = True

    reliability_reason = str(d06_summary.get("reason_code") or "")
    reliability_env_gap = reliability_reason in {"INSUFFICIENT_RUNS_ENV_GAP", "SKIP_RATE_HIGH_ENV_GAP"} or (
        to_float(d06_metrics.get("env_gap_ratio", 0.0), 0.0) >= float(env_gap_waiver_min_rate)
    )

    candidate_count = to_int(d02_metrics.get("candidate_count", 0), 0)
    action_count = len(list(d02.get("collection_actions", [])))
    taxonomy_feedback_active = candidate_count > 0 and action_count > 0

    return {
        "provider_env_gap": provider_env_gap,
        "notify_not_attempted": notify_not_attempted,
        "reliability_env_gap": reliability_env_gap,
        "taxonomy_feedback_active": taxonomy_feedback_active,
        "taxonomy_candidate_count": candidate_count,
        "taxonomy_action_count": action_count,
        "unknown_ratio": to_float(d02_metrics.get("unknown_ratio", 0.0), 0.0),
    }


def apply_metric_waivers(
    hard: List[Dict[str, Any]],
    *,
    context: Dict[str, Any],
    taxonomy_waiver_min_candidates: int,
    taxonomy_waiver_max_unknown: float,
) -> Dict[str, Any]:
    remaining: List[Dict[str, Any]] = []
    waived: List[Dict[str, Any]] = []
    softened: List[Dict[str, Any]] = []

    for row in hard:
        metric = str(dict(row).get("metric") or "")
        waiver_code = ""
        waiver_note = ""

        if metric == "skip_rate" and _to_bool(context.get("provider_env_gap")):
            waiver_code = WAIVER_SKIP_RATE_ENV_GAP
            waiver_note = "skip degradation is dominated by provider environment gap."
        elif metric == "notify_delivery_rate" and _to_bool(context.get("notify_not_attempted")):
            waiver_code = WAIVER_NOTIFY_NOT_ATTEMPTED
            waiver_note = "notification was intentionally not attempted in current environment."
        elif metric == "reliability_total_runs" and _to_bool(context.get("reliability_env_gap")):
            waiver_code = WAIVER_RELIABILITY_ENV_GAP
            waiver_note = "insufficient soak runs are caused by provider environment gap."
        elif metric == "unknown_ratio":
            candidate_count = to_int(context.get("taxonomy_candidate_count", 0), 0)
            unknown_ratio = to_float(context.get("unknown_ratio", 0.0), 0.0)
            if (
                _to_bool(context.get("taxonomy_feedback_active"))
                and candidate_count >= max(1, int(taxonomy_waiver_min_candidates))
                and unknown_ratio <= float(taxonomy_waiver_max_unknown)
            ):
                waiver_code = WAIVER_UNKNOWN_RATIO_WITH_ACTIONS
                waiver_note = "taxonomy feedback actions are active and candidate backlog is populated."

        if not waiver_code:
            remaining.append(row)
            continue

        waived_row = {
            **row,
            "waiver_code": waiver_code,
            "waiver_note": waiver_note,
            "waived_to": "soft",
        }
        softened_row = {
            **row,
            "waived_from_hard": True,
            "waiver_code": waiver_code,
            "waiver_note": waiver_note,
        }
        waived.append(waived_row)
        softened.append(softened_row)

    return {
        "hard": remaining,
        "waived_hard": waived,
        "soft_from_hard": softened,
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    metrics = dict(payload.get("metrics", {}))
    lines: List[str] = []
    lines.append("# S28-09 SLO Readiness v2 (Latest)")
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
    lines.append(f"- waived_hard: `{summary.get('waived_hard_count', 0)}`")
    lines.append("")
    lines.append("## SLO Metrics")
    lines.append("")
    lines.append(f"- skip_rate: `{metrics.get('skip_rate', 0.0)}`")
    lines.append(f"- unknown_ratio: `{metrics.get('unknown_ratio', 0.0)}`")
    lines.append(f"- acceptance_pass_rate: `{metrics.get('acceptance_pass_rate', 0.0)}`")
    lines.append(f"- notify_delivery_rate: `{metrics.get('notify_delivery_rate', 0.0)}`")
    lines.append(f"- reliability_total_runs: `{metrics.get('reliability_total_runs', 0)}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--skip-rate-soft", type=float, default=0.20)
    parser.add_argument("--skip-rate-hard", type=float, default=0.50)
    parser.add_argument("--unknown-ratio-soft", type=float, default=0.05)
    parser.add_argument("--unknown-ratio-hard", type=float, default=0.25)
    parser.add_argument("--acceptance-pass-rate-soft", type=float, default=0.95)
    parser.add_argument("--acceptance-pass-rate-hard", type=float, default=0.85)
    parser.add_argument("--notify-delivery-soft", type=float, default=0.95)
    parser.add_argument("--notify-delivery-hard", type=float, default=0.50)
    parser.add_argument("--reliability-runs-soft-min", type=int, default=24)
    parser.add_argument("--reliability-runs-hard-min", type=int, default=12)
    parser.add_argument("--disable-waivers", action="store_true")
    parser.add_argument("--env-gap-waiver-min-rate", type=float, default=0.8)
    parser.add_argument("--taxonomy-waiver-min-candidates", type=int, default=5)
    parser.add_argument("--taxonomy-waiver-max-unknown", type=float, default=0.35)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s28-slo-readiness-v2", obs_root=args.obs_root)

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
        reln = head_relation(repo_root, str(dict(doc.get("git", {})).get("head") or ""), current_head)
        if is_stale_artifact(doc, current_head, repo_root):
            stale.append(phase)
            emit("ERROR", f"stale phase={phase}", events)
            docs[phase] = {}
            continue
        if reln == "ancestor":
            emit("WARN", f"head behind but acceptable phase={phase}", events)
        docs[phase] = doc
        emit("OK", f"loaded phase={phase}", events)

    gates = build_gate_rows(docs)
    for row in gates:
        level = "OK" if row["passed"] else "ERROR"
        emit(level, f"gate={row['phase']} passed={row['passed']} actual={row['actual']}", events)

    passed_gates = sum(1 for g in gates if g["passed"])
    blocked_gates = len(gates) - passed_gates

    d01 = docs.get("S28-01", {})
    d02 = docs.get("S28-02", {})
    d03 = docs.get("S28-03", {})
    d06 = docs.get("S28-06", {})
    d07 = docs.get("S28-07", {})

    skip_rate = to_float(dict(d01.get("trend", {})).get("skip_rate", 0.0), 0.0)
    unknown_ratio = to_float(dict(d02.get("metrics", {})).get("unknown_ratio", 0.0), 0.0)

    notify_doc = dict(d03.get("notification", {}))
    notify_sent = bool(notify_doc.get("sent", False))
    notify_attempted = bool(notify_doc.get("attempted", False))
    notify_attempt_count = to_int(notify_doc.get("attempt_count", 0), 0)
    if notify_attempt_count <= 0 and notify_attempted:
        notify_attempt_count = 1
    notify_success_count = 1 if notify_sent else 0
    delivery_rate_raw = notify_doc.get("delivery_rate", None)
    if delivery_rate_raw is None or str(delivery_rate_raw).strip() == "":
        notify_delivery_rate = compute_notify_delivery_rate(
            notify_sent=notify_sent,
            notify_attempt_count=notify_attempt_count,
            notify_attempted=notify_attempted,
        )
    else:
        notify_delivery_rate = to_float(delivery_rate_raw, 0.0)
    reliability_total_runs = to_int(dict(d06.get("metrics", {})).get("total_runs", 0), 0)

    acc_sum = dict(d07.get("summary", {}))
    acc_total = to_int(acc_sum.get("total_cases", 0), 0)
    acc_passed = to_int(acc_sum.get("passed_cases", 0), 0)
    acceptance_pass_rate = 0.0 if acc_total <= 0 else round(acc_passed / float(acc_total), 4)

    slo_eval = evaluate_slo(
        skip_rate=skip_rate,
        unknown_ratio=unknown_ratio,
        acceptance_pass_rate=acceptance_pass_rate,
        notify_delivery_rate=notify_delivery_rate,
        reliability_total_runs=reliability_total_runs,
        skip_soft=float(args.skip_rate_soft),
        skip_hard=float(args.skip_rate_hard),
        unknown_soft=float(args.unknown_ratio_soft),
        unknown_hard=float(args.unknown_ratio_hard),
        acceptance_soft=float(args.acceptance_pass_rate_soft),
        acceptance_hard=float(args.acceptance_pass_rate_hard),
        notify_soft=float(args.notify_delivery_soft),
        notify_hard=float(args.notify_delivery_hard),
        reliability_runs_soft_min=max(int(args.reliability_runs_soft_min), 1),
        reliability_runs_hard_min=max(int(args.reliability_runs_hard_min), 1),
    )

    hard = list(slo_eval.get("hard", []))
    soft = list(slo_eval.get("soft", []))
    waived_hard: List[Dict[str, Any]] = []
    if not bool(args.disable_waivers):
        waiver_context = build_waiver_context(
            d01=d01,
            d02=d02,
            d03=d03,
            d06=d06,
            env_gap_waiver_min_rate=float(args.env_gap_waiver_min_rate),
        )
        waiver_out = apply_metric_waivers(
            hard,
            context=waiver_context,
            taxonomy_waiver_min_candidates=max(1, int(args.taxonomy_waiver_min_candidates)),
            taxonomy_waiver_max_unknown=float(args.taxonomy_waiver_max_unknown),
        )
        hard = list(waiver_out.get("hard", []))
        waived_hard = list(waiver_out.get("waived_hard", []))
        soft = list(soft) + list(waiver_out.get("soft_from_hard", []))
    else:
        waiver_context = {
            "provider_env_gap": False,
            "notify_not_attempted": False,
            "reliability_env_gap": False,
            "taxonomy_feedback_active": False,
            "taxonomy_candidate_count": 0,
            "taxonomy_action_count": 0,
            "unknown_ratio": unknown_ratio,
        }

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

    if waived_hard:
        emit("WARN", f"waivers applied count={len(waived_hard)}", events)

    if status == "FAIL":
        emit("ERROR", f"slo v2 readiness=BLOCKED reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"slo v2 readiness=WARN_ONLY reason={reason_code}", events)
    else:
        emit("OK", "slo v2 readiness=READY", events)

    payload: Dict[str, Any] = {
        "schema_version": "s28-slo-readiness-v2",
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
            "notify_delivery_rate": notify_delivery_rate,
            "notify_attempt_count": notify_attempt_count,
            "notify_success_count": notify_success_count,
            "notify_delivery_state": str(notify_doc.get("delivery_state") or ""),
            "reliability_total_runs": reliability_total_runs,
        },
        "slo": {
            "hard_violations": hard,
            "soft_violations": soft,
            "waived_hard_violations": waived_hard,
            "waiver_context": waiver_context,
            "thresholds": {
                "skip_rate_soft": float(args.skip_rate_soft),
                "skip_rate_hard": float(args.skip_rate_hard),
                "unknown_ratio_soft": float(args.unknown_ratio_soft),
                "unknown_ratio_hard": float(args.unknown_ratio_hard),
                "acceptance_pass_rate_soft": float(args.acceptance_pass_rate_soft),
                "acceptance_pass_rate_hard": float(args.acceptance_pass_rate_hard),
                "notify_delivery_soft": float(args.notify_delivery_soft),
                "notify_delivery_hard": float(args.notify_delivery_hard),
                "reliability_runs_soft_min": max(int(args.reliability_runs_soft_min), 1),
                "reliability_runs_hard_min": max(int(args.reliability_runs_hard_min), 1),
                "waivers_enabled": not bool(args.disable_waivers),
                "env_gap_waiver_min_rate": float(args.env_gap_waiver_min_rate),
                "taxonomy_waiver_min_candidates": max(1, int(args.taxonomy_waiver_min_candidates)),
                "taxonomy_waiver_max_unknown": float(args.taxonomy_waiver_max_unknown),
            },
        },
        "summary": {
            "readiness": readiness,
            "status": status,
            "reason_code": reason_code,
            "total_gates": len(gates),
            "passed_gates": passed_gates,
            "blocked_gates": blocked_gates,
            "blocked_total": int(blocked_gates) + len(hard),
            "hard_block_count": len(hard),
            "soft_warn_count": len(soft),
            "waived_hard_count": len(waived_hard),
            "missing_count": len(missing),
            "stale_count": len(stale),
        },
        "artifact_names": {"json": "slo_readiness_v2_latest.json", "md": "slo_readiness_v2_latest.md"},
    }

    out_json = out_dir / "slo_readiness_v2_latest.json"
    out_md = out_dir / "slo_readiness_v2_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"readiness": readiness, "status": status, "reason_code": reason_code})
    return 0 if readiness != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
