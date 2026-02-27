#!/usr/bin/env python3
"""
S27-01 provider canary operations runner.

Goal:
- Reuse S26 provider canary checks.
- Track skip-rate trend over a rolling window.
- Emit operational PASS/WARN/FAIL decision for continuous monitoring.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CONFIG = "docs/ops/S27-01_PROVIDER_CANARY_OPS.toml"
DEFAULT_OUT_DIR = "docs/evidence/s27-01"
DEFAULT_HISTORY = "provider_canary_history.json"
DEFAULT_WINDOW = 6
DEFAULT_SKIP_WARN_THRESHOLD = 0.40
DEFAULT_MAX_HISTORY = 200

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_BASE_CANARY_FAILED = "BASE_CANARY_FAILED"
REASON_BASE_ARTIFACT_MISSING = "BASE_ARTIFACT_MISSING"
REASON_SKIP_RATE_HIGH = "SKIP_RATE_HIGH"
REASON_RECENT_FAILURE = "RECENT_FAILURE"


def _read_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("tomllib unavailable")
    return tomllib.loads(path.read_text(encoding="utf-8"))


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


def validate_config(cfg: Dict[str, Any]) -> str:
    if str(cfg.get("schema_version") or "") != "s26-provider-canary-v1":
        return "schema_version must keep s26-provider-canary-v1 for compatibility"
    if str(cfg.get("ops_schema_version") or "") != "s27-provider-canary-ops-v1":
        return "ops_schema_version mismatch"
    ops = cfg.get("ops_policy")
    if not isinstance(ops, dict):
        return "ops_policy missing"
    try:
        win = int(ops.get("window_size", DEFAULT_WINDOW))
        if win <= 0:
            return "ops_policy.window_size must be > 0"
    except Exception:
        return "ops_policy.window_size invalid"
    try:
        thr = float(ops.get("skip_rate_warn_threshold", DEFAULT_SKIP_WARN_THRESHOLD))
        if thr < 0 or thr > 1:
            return "ops_policy.skip_rate_warn_threshold must be in [0,1]"
    except Exception:
        return "ops_policy.skip_rate_warn_threshold invalid"
    try:
        max_hist = int(ops.get("max_history_entries", DEFAULT_MAX_HISTORY))
        if max_hist <= 0:
            return "ops_policy.max_history_entries must be > 0"
    except Exception:
        return "ops_policy.max_history_entries invalid"
    return ""


def run_base_canary(repo_root: Path, config_path: Path, out_dir: Path, strict_provider_env: bool, timeout_sec: int) -> Dict[str, Any]:
    cmd = [
        "python3",
        "scripts/ops/s26_provider_canary.py",
        "--config",
        str(config_path),
        "--out-dir",
        to_repo_rel(repo_root, out_dir),
    ]
    if strict_provider_env:
        cmd.append("--strict-provider-env")
    if timeout_sec > 0:
        cmd.extend(["--timeout-sec", str(timeout_sec)])

    cp = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=False)
    return {
        "command": cmd,
        "returncode": int(cp.returncode),
        "stdout": cp.stdout or "",
        "stderr": cp.stderr or "",
    }


def build_run_entry(base_doc: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(base_doc.get("summary", {}))
    return {
        "captured_at_utc": str(base_doc.get("captured_at_utc") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        "status": str(summary.get("status") or ""),
        "reason_code": str(summary.get("reason_code") or ""),
        "passed_cases": int(summary.get("passed_cases", 0) or 0),
        "failed_cases": int(summary.get("failed_cases", 0) or 0),
        "skipped_cases": int(summary.get("skipped_cases", 0) or 0),
    }


def update_history(history_doc: Dict[str, Any], run_entry: Dict[str, Any], max_entries: int) -> Dict[str, Any]:
    runs = list(history_doc.get("runs", [])) if isinstance(history_doc.get("runs"), list) else []
    runs.append(run_entry)
    if len(runs) > max_entries:
        runs = runs[-max_entries:]
    return {
        "schema_version": "s27-provider-canary-history-v1",
        "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runs": runs,
    }


def window_metrics(runs: List[Dict[str, Any]], window_size: int) -> Dict[str, Any]:
    if window_size <= 0:
        window_size = 1
    window = runs[-window_size:]
    total = len(window)
    if total == 0:
        return {
            "window_size": window_size,
            "window_count": 0,
            "skip_rate": 0.0,
            "fail_rate": 0.0,
            "warn_rate": 0.0,
            "skip_runs": 0,
            "fail_runs": 0,
            "warn_runs": 0,
        }
    skip_runs = sum(1 for x in window if str(x.get("status") or "").upper() == "SKIP")
    fail_runs = sum(1 for x in window if str(x.get("status") or "").upper() == "FAIL")
    warn_runs = sum(1 for x in window if str(x.get("status") or "").upper() == "WARN")
    return {
        "window_size": window_size,
        "window_count": total,
        "skip_rate": round(skip_runs / float(total), 4),
        "fail_rate": round(fail_runs / float(total), 4),
        "warn_rate": round(warn_runs / float(total), 4),
        "skip_runs": skip_runs,
        "fail_runs": fail_runs,
        "warn_runs": warn_runs,
    }


def decide_ops_status(base_status: str, base_rc: int, metrics: Dict[str, Any], skip_warn_threshold: float, warn_on_recent_failures: bool) -> Dict[str, str]:
    base_status_u = str(base_status or "").upper()
    if base_rc != 0 or base_status_u == "FAIL":
        return {"status": "FAIL", "reason_code": REASON_BASE_CANARY_FAILED}
    if warn_on_recent_failures and int(metrics.get("fail_runs", 0)) > 0:
        return {"status": "WARN", "reason_code": REASON_RECENT_FAILURE}
    if float(metrics.get("skip_rate", 0.0)) > float(skip_warn_threshold):
        return {"status": "WARN", "reason_code": REASON_SKIP_RATE_HIGH}
    return {"status": "PASS", "reason_code": ""}


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    trend = dict(payload.get("trend", {}))
    lines: List[str] = []
    lines.append("# S27-01 Provider Canary Ops (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- base_status: `{summary.get('base_status', '')}`")
    lines.append(f"- base_returncode: `{summary.get('base_returncode', '')}`")
    lines.append("")
    lines.append("## Trend")
    lines.append("")
    lines.append(f"- window_count: `{trend.get('window_count', 0)}`")
    lines.append(f"- skip_rate: `{trend.get('skip_rate', 0.0)}`")
    lines.append(f"- fail_rate: `{trend.get('fail_rate', 0.0)}`")
    lines.append(f"- warn_threshold: `{payload.get('ops_policy', {}).get('skip_rate_warn_threshold', 0.0)}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S27-01 Provider Canary Ops")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- base_status_rc: {summary.get('base_status', '')}/{summary.get('base_returncode', '')}")
    lines.append(f"- skip_rate_window: {trend.get('skip_rate', 0.0)} (n={trend.get('window_count', 0)})")
    lines.append(f"- history_size: {summary.get('history_size', 0)}")
    lines.append(f"- artifact: docs/evidence/s27-01/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure_artifacts(repo_root: Path, out_dir: Path, reason_code: str, message: str) -> None:
    payload: Dict[str, Any] = {
        "schema_version": "s27-provider-canary-ops-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "ops_policy": {},
        "base": {
            "artifact": "",
            "summary": {},
            "execution": {},
        },
        "trend": {
            "window_size": 0,
            "window_count": 0,
            "skip_rate": 0.0,
            "fail_rate": 0.0,
            "warn_rate": 0.0,
            "skip_runs": 0,
            "fail_runs": 0,
            "warn_runs": 0,
        },
        "summary": {
            "status": "FAIL",
            "reason_code": reason_code,
            "base_status": "",
            "base_returncode": 1,
            "history_size": 0,
            "errors": [message],
        },
        "artifact_names": {
            "json": "provider_canary_ops_latest.json",
            "md": "provider_canary_ops_latest.md",
            "history": DEFAULT_HISTORY,
        },
    }
    out_json = out_dir / "provider_canary_ops_latest.json"
    out_md = out_dir / "provider_canary_ops_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--history-file", default=DEFAULT_HISTORY)
    parser.add_argument("--timeout-sec", type=int, default=0)
    parser.add_argument("--strict-provider-env", action="store_true")
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s27-provider-canary-ops", obs_root=args.obs_root)

    config_path = (repo_root / args.config).resolve()
    if not config_path.exists():
        msg = f"config missing path={config_path}"
        emit("ERROR", msg, events)
        write_failure_artifacts(repo_root, out_dir, REASON_CONFIG_INVALID, msg)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cfg = _read_toml(config_path)
    except Exception as exc:
        msg = f"config parse failed err={exc}"
        emit("ERROR", msg, events)
        write_failure_artifacts(repo_root, out_dir, REASON_CONFIG_INVALID, msg)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    reason = validate_config(cfg)
    if reason:
        emit("ERROR", f"config invalid reason={reason}", events)
        write_failure_artifacts(repo_root, out_dir, REASON_CONFIG_INVALID, reason)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    ops_policy = dict(cfg.get("ops_policy") or {})
    window_size = int(ops_policy.get("window_size", DEFAULT_WINDOW))
    skip_warn_threshold = float(ops_policy.get("skip_rate_warn_threshold", DEFAULT_SKIP_WARN_THRESHOLD))
    max_history_entries = int(ops_policy.get("max_history_entries", DEFAULT_MAX_HISTORY))
    warn_on_recent_failures = bool(ops_policy.get("warn_on_recent_failures", True))

    base_exec = run_base_canary(
        repo_root=repo_root,
        config_path=config_path,
        out_dir=out_dir,
        strict_provider_env=bool(args.strict_provider_env),
        timeout_sec=int(args.timeout_sec),
    )
    emit("OK", f"base_canary_rc={base_exec['returncode']}", events)

    base_artifact = out_dir / "provider_canary_latest.json"
    base_doc = read_json_if_exists(base_artifact)
    if not base_doc:
        msg = f"base artifact missing path={base_artifact}"
        emit("ERROR", msg, events)
        write_failure_artifacts(repo_root, out_dir, REASON_BASE_ARTIFACT_MISSING, msg)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_BASE_ARTIFACT_MISSING})
        return 1

    history_path = out_dir / str(args.history_file)
    history_doc = read_json_if_exists(history_path)
    run_entry = build_run_entry(base_doc)
    history_doc = update_history(history_doc, run_entry, max_entries=max_history_entries)
    history_path.write_text(json.dumps(history_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    runs = list(history_doc.get("runs", [])) if isinstance(history_doc.get("runs"), list) else []
    trend = window_metrics(runs, window_size=window_size)
    base_summary = dict(base_doc.get("summary", {}))
    decision = decide_ops_status(
        base_status=str(base_summary.get("status") or ""),
        base_rc=int(base_exec.get("returncode", 1)),
        metrics=trend,
        skip_warn_threshold=skip_warn_threshold,
        warn_on_recent_failures=warn_on_recent_failures,
    )

    status = decision["status"]
    reason_code = decision["reason_code"]
    if status == "FAIL":
        emit("ERROR", f"ops status=FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"ops status=WARN reason={reason_code}", events)
    else:
        emit("OK", "ops status=PASS", events)

    payload: Dict[str, Any] = {
        "schema_version": "s27-provider-canary-ops-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "config_path": to_repo_rel(repo_root, config_path),
        "ops_policy": {
            "window_size": window_size,
            "skip_rate_warn_threshold": skip_warn_threshold,
            "max_history_entries": max_history_entries,
            "warn_on_recent_failures": warn_on_recent_failures,
        },
        "base": {
            "artifact": to_repo_rel(repo_root, base_artifact),
            "summary": base_summary,
            "execution": {
                "command": base_exec["command"],
                "returncode": base_exec["returncode"],
                "stdout_tail": (base_exec["stdout"] or "")[-1000:],
                "stderr_tail": (base_exec["stderr"] or "")[-1000:],
            },
        },
        "trend": trend,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "base_status": str(base_summary.get("status") or ""),
            "base_returncode": int(base_exec["returncode"]),
            "history_size": len(runs),
        },
        "artifact_names": {
            "json": "provider_canary_ops_latest.json",
            "md": "provider_canary_ops_latest.md",
            "history": str(args.history_file),
        },
    }

    out_json = out_dir / "provider_canary_ops_latest.json"
    out_md = out_dir / "provider_canary_ops_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)
    emit("OK", f"history_json={history_path}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "skip_rate": trend.get("skip_rate", 0.0)})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
