#!/usr/bin/env python3
"""
S30-02 quality burndown automation.

Encode S29 closeout carry-over work as deterministic checks:
- 5 waiver exit-condition checks
- 14 unresolved-risk checks
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s30-02"
INPUTS = {
    "closeout": "docs/evidence/s29-10/closeout_latest.json",
    "readiness": "docs/evidence/s29-09/slo_readiness_v4_latest.json",
    "canary": "docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json",
    "taxonomy": "docs/evidence/s29-02/taxonomy_pipeline_integration_latest.json",
    "notify": "docs/evidence/s29-03/readiness_notify_multichannel_latest.json",
    "soak": "docs/evidence/s29-06/reliability_soak_v4_latest.json",
    "trend": "docs/evidence/s29-08/evidence_trend_index_v5_latest.json",
}


def read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


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


def as_check(
    check_id: str,
    bucket: str,
    title: str,
    status: str,
    *,
    target: str,
    observed: Any,
    detail: str,
) -> Dict[str, Any]:
    fixed = "PASS" if str(status).upper() == "PASS" else "WARN"
    return {
        "id": check_id,
        "bucket": bucket,
        "title": title,
        "status": fixed,
        "done": fixed == "PASS",
        "target": target,
        "observed": observed,
        "detail": detail,
    }


def evaluate_checks(
    *,
    closeout: Dict[str, Any],
    readiness: Dict[str, Any],
    canary: Dict[str, Any],
    taxonomy: Dict[str, Any],
    notify: Dict[str, Any],
    soak: Dict[str, Any],
    trend: Dict[str, Any],
) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    metrics = dict(readiness.get("metrics", {}))
    slo = dict(readiness.get("slo", {}))
    waived = list(slo.get("waived_hard_violations", []))
    waived_metrics = {str(dict(row).get("metric") or "") for row in waived}

    canary_trend = dict(canary.get("trend", {}))
    trailing_streak = to_int(canary_trend.get("trailing_nonpass_streak", 0), 0)
    unknown_ratio = to_float(dict(taxonomy.get("metrics", {})).get("unknown_ratio", 0.0), 0.0)

    channels = list(notify.get("channels", []))
    all_webhook_ok = len(channels) > 0
    for row in channels:
        item = dict(row)
        attempted = bool(item.get("attempted", False))
        sent = bool(item.get("sent", False))
        code = to_int(item.get("http_status", 0), 0)
        if not attempted or not sent or code < 200 or code >= 300:
            all_webhook_ok = False
            break

    soak_metrics = dict(soak.get("metrics", {}))
    soak_summary = dict(soak.get("summary", {}))
    total_runs = to_int(soak_metrics.get("total_runs", 0), 0)

    checks.append(
        as_check(
            "WVR-01",
            "waiver_exit",
            "skip_rate trailing non-pass streak < 3",
            "PASS" if trailing_streak < 3 else "WARN",
            target="streak < 3",
            observed=trailing_streak,
            detail="Derived from s29-01 trend.trailing_nonpass_streak.",
        )
    )
    checks.append(
        as_check(
            "WVR-02",
            "waiver_exit",
            "unknown_ratio <= 0.03",
            "PASS" if unknown_ratio <= 0.03 else "WARN",
            target="<= 0.03",
            observed=unknown_ratio,
            detail="Derived from s29-02 metrics.unknown_ratio.",
        )
    )
    checks.append(
        as_check(
            "WVR-03",
            "waiver_exit",
            "notify channels return 2xx at least once",
            "PASS" if all_webhook_ok else "WARN",
            target="all channels attempted+sent with HTTP 2xx",
            observed={
                "channel_count": len(channels),
                "all_ok": all_webhook_ok,
            },
            detail="Derived from s29-03 channels[*].attempted/sent/http_status.",
        )
    )
    checks.append(
        as_check(
            "WVR-04",
            "waiver_exit",
            "recovery_success_rate streak condition",
            "PASS" if trailing_streak < 3 else "WARN",
            target="streak < 3",
            observed=trailing_streak,
            detail="Same operational streak guard as skip_rate for RECOVERY_SUCCESS_ENV_GAP.",
        )
    )
    checks.append(
        as_check(
            "WVR-05",
            "waiver_exit",
            "reliability soak rerun with enough runs",
            "PASS" if total_runs >= 24 and str(soak_summary.get("status") or "") == "PASS" else "WARN",
            target="total_runs >= 24 and status PASS",
            observed={"total_runs": total_runs, "status": str(soak_summary.get("status") or "")},
            detail="Derived from s29-06 metrics.total_runs and summary.status.",
        )
    )

    skip_rate = to_float(metrics.get("skip_rate", 0.0), 0.0)
    notify_rate = to_float(metrics.get("notify_delivery_rate", 0.0), 0.0)
    recovery_rate = to_float(metrics.get("recovery_success_rate", 0.0), 0.0)
    reliability_runs = to_int(metrics.get("reliability_total_runs", 0), 0)

    checks.extend(
        [
            as_check("RSK-01", "unresolved_risk", "skip_rate soft SLO monitor", "PASS" if skip_rate <= 0.15 else "WARN", target="<= 0.15", observed=skip_rate, detail="s29-09 metrics.skip_rate"),
            as_check("RSK-02", "unresolved_risk", "unknown_ratio soft SLO monitor", "PASS" if unknown_ratio <= 0.03 else "WARN", target="<= 0.03", observed=unknown_ratio, detail="s29-02 metrics.unknown_ratio"),
            as_check("RSK-03", "unresolved_risk", "notify_delivery_rate soft SLO monitor", "PASS" if notify_rate >= 1.0 else "WARN", target=">= 1.0", observed=notify_rate, detail="s29-09 metrics.notify_delivery_rate"),
            as_check("RSK-04", "unresolved_risk", "recovery_success_rate soft SLO monitor", "PASS" if recovery_rate >= 0.8 else "WARN", target=">= 0.8", observed=recovery_rate, detail="s29-09 metrics.recovery_success_rate"),
            as_check("RSK-05", "unresolved_risk", "reliability_total_runs soft SLO monitor", "PASS" if reliability_runs >= 24 else "WARN", target=">= 24", observed=reliability_runs, detail="s29-09 metrics.reliability_total_runs"),
            as_check("RSK-06", "unresolved_risk", "skip_rate waiver removed", "PASS" if "skip_rate" not in waived_metrics else "WARN", target="waived_hard does not include skip_rate", observed=sorted(waived_metrics), detail="s29-09 slo.waived_hard_violations"),
            as_check("RSK-07", "unresolved_risk", "unknown_ratio waiver removed", "PASS" if "unknown_ratio" not in waived_metrics else "WARN", target="waived_hard does not include unknown_ratio", observed=sorted(waived_metrics), detail="s29-09 slo.waived_hard_violations"),
            as_check("RSK-08", "unresolved_risk", "notify_delivery_rate waiver removed", "PASS" if "notify_delivery_rate" not in waived_metrics else "WARN", target="waived_hard does not include notify_delivery_rate", observed=sorted(waived_metrics), detail="s29-09 slo.waived_hard_violations"),
            as_check("RSK-09", "unresolved_risk", "recovery_success_rate waiver removed", "PASS" if "recovery_success_rate" not in waived_metrics else "WARN", target="waived_hard does not include recovery_success_rate", observed=sorted(waived_metrics), detail="s29-09 slo.waived_hard_violations"),
            as_check("RSK-10", "unresolved_risk", "reliability_total_runs waiver removed", "PASS" if "reliability_total_runs" not in waived_metrics else "WARN", target="waived_hard does not include reliability_total_runs", observed=sorted(waived_metrics), detail="s29-09 slo.waived_hard_violations"),
            as_check("RSK-11", "unresolved_risk", "evidence trend warning phases reduced to 0", "PASS" if to_int(dict(trend.get("summary", {})).get("warn_count", 0), 0) == 0 else "WARN", target="warn_count == 0", observed=to_int(dict(trend.get("summary", {})).get("warn_count", 0), 0), detail="s29-08 summary.warn_count"),
            as_check("RSK-12", "unresolved_risk", "provider env gap skip chronicity resolved", "PASS" if to_float(canary_trend.get("env_skip_rate", 0.0), 0.0) < 0.8 else "WARN", target="env_skip_rate < 0.8", observed=to_float(canary_trend.get("env_skip_rate", 0.0), 0.0), detail="s29-01 trend.env_skip_rate"),
            as_check(
                "RSK-13",
                "unresolved_risk",
                "retry/backoff tuning validated",
                "PASS" if to_int(dict(notify.get("inputs", {})).get("max_retries", 0), 0) >= 2 and to_float(dict(notify.get("inputs", {})).get("retry_backoff_sec", 0.0), 0.0) >= 1.0 else "WARN",
                target="max_retries>=2 and retry_backoff_sec>=1.0",
                observed={
                    "max_retries": to_int(dict(notify.get("inputs", {})).get("max_retries", 0), 0),
                    "retry_backoff_sec": to_float(dict(notify.get("inputs", {})).get("retry_backoff_sec", 0.0), 0.0),
                },
                detail="s29-03 inputs retry settings.",
            ),
            as_check(
                "RSK-14",
                "unresolved_risk",
                "unknown taxonomy chronic issue resolved",
                "PASS" if unknown_ratio <= 0.03 and to_int(dict(taxonomy.get("metrics", {})).get("candidate_count", 0), 0) <= 2 else "WARN",
                target="unknown_ratio<=0.03 and candidate_count<=2",
                observed={
                    "unknown_ratio": unknown_ratio,
                    "candidate_count": to_int(dict(taxonomy.get("metrics", {})).get("candidate_count", 0), 0),
                },
                detail="s29-02 metrics unknown_ratio/candidate_count.",
            ),
        ]
    )

    return checks


def summarize(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    waiver = [c for c in checks if str(c.get("bucket")) == "waiver_exit"]
    risks = [c for c in checks if str(c.get("bucket")) == "unresolved_risk"]

    waiver_done = sum(1 for c in waiver if bool(c.get("done")))
    risk_done = sum(1 for c in risks if bool(c.get("done")))
    total = len(checks)
    done = waiver_done + risk_done
    remaining = total - done

    return {
        "status": "PASS" if remaining == 0 else "WARN",
        "total_checks": total,
        "done_checks": done,
        "remaining_checks": remaining,
        "waiver_total": len(waiver),
        "waiver_done": waiver_done,
        "waiver_remaining": len(waiver) - waiver_done,
        "risk_total": len(risks),
        "risk_done": risk_done,
        "risk_remaining": len(risks) - risk_done,
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    checks = list(payload.get("checks", []))

    lines: List[str] = []
    lines.append("# S30-02 Quality Burndown (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{dict(payload.get('git', {})).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{dict(payload.get('git', {})).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- total_checks: `{summary.get('total_checks', 0)}`")
    lines.append(f"- done_checks: `{summary.get('done_checks', 0)}`")
    lines.append(f"- remaining_checks: `{summary.get('remaining_checks', 0)}`")
    lines.append(f"- waiver_done/total: `{summary.get('waiver_done', 0)}/{summary.get('waiver_total', 0)}`")
    lines.append(f"- risk_done/total: `{summary.get('risk_done', 0)}/{summary.get('risk_total', 0)}`")
    lines.append("")

    lines.append("## Checks")
    lines.append("")
    for row in checks:
        lines.append(
            "- [{status}] {id} ({bucket}) {title} | target={target} | observed={observed}".format(
                status=str(row.get("status") or "WARN"),
                id=str(row.get("id") or ""),
                bucket=str(row.get("bucket") or ""),
                title=str(row.get("title") or ""),
                target=str(row.get("target") or ""),
                observed=json.dumps(row.get("observed"), ensure_ascii=False, sort_keys=True),
            )
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--closeout-json", default=INPUTS["closeout"])
    parser.add_argument("--readiness-json", default=INPUTS["readiness"])
    parser.add_argument("--canary-json", default=INPUTS["canary"])
    parser.add_argument("--taxonomy-json", default=INPUTS["taxonomy"])
    parser.add_argument("--notify-json", default=INPUTS["notify"])
    parser.add_argument("--soak-json", default=INPUTS["soak"])
    parser.add_argument("--trend-json", default=INPUTS["trend"])
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    run_dir, meta, events = make_run_context(repo_root, tool="s30-quality-burndown", obs_root=args.obs_root)

    closeout = read_json_if_exists((repo_root / args.closeout_json).resolve())
    readiness = read_json_if_exists((repo_root / args.readiness_json).resolve())
    canary = read_json_if_exists((repo_root / args.canary_json).resolve())
    taxonomy = read_json_if_exists((repo_root / args.taxonomy_json).resolve())
    notify = read_json_if_exists((repo_root / args.notify_json).resolve())
    soak = read_json_if_exists((repo_root / args.soak_json).resolve())
    trend = read_json_if_exists((repo_root / args.trend_json).resolve())

    docs = {
        "closeout": closeout,
        "readiness": readiness,
        "canary": canary,
        "taxonomy": taxonomy,
        "notify": notify,
        "soak": soak,
        "trend": trend,
    }
    for key, doc in docs.items():
        if doc:
            emit("OK", f"loaded {key}", events)
        else:
            emit("ERROR", f"missing {key}", events)

    checks = evaluate_checks(
        closeout=closeout,
        readiness=readiness,
        canary=canary,
        taxonomy=taxonomy,
        notify=notify,
        soak=soak,
        trend=trend,
    )
    summary = summarize(checks)

    for row in checks:
        emit("OK" if bool(row.get("done")) else "WARN", f"{row.get('id')} status={row.get('status')}", events)

    payload = {
        "schema_version": "s30-quality-burndown-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "closeout_json": args.closeout_json,
            "readiness_json": args.readiness_json,
            "canary_json": args.canary_json,
            "taxonomy_json": args.taxonomy_json,
            "notify_json": args.notify_json,
            "soak_json": args.soak_json,
            "trend_json": args.trend_json,
        },
        "summary": summary,
        "checks": checks,
        "closeout_snapshot": {
            "waived_hard_count": to_int(dict(closeout.get("summary", {})).get("waived_hard_count", 0), 0),
            "unresolved_risk_count": to_int(dict(closeout.get("summary", {})).get("unresolved_risk_count", 0), 0),
        },
        "artifact_names": {
            "json": "quality_burndown_latest.json",
            "md": "quality_burndown_latest.md",
        },
    }

    out_json = out_dir / "quality_burndown_latest.json"
    out_md = out_dir / "quality_burndown_latest.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": summary.get("status"), "remaining_checks": summary.get("remaining_checks", 0)})

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if str(summary.get("status") or "") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
