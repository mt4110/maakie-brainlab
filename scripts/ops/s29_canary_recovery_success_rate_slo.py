#!/usr/bin/env python3
"""
S29-01 canary recovery success-rate SLO v2.

Goal:
- Detect sustained non-pass streaks from canary history.
- Provide deterministic recovery actions and optional auto-recovery execution.
- Evaluate recovery success-rate SLO from canary history transitions.
- Persist explicit exit conditions for WARN/FAIL states.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CONFIG = "docs/ops/S29-01_CANARY_RECOVERY_SUCCESS_RATE_SLO.toml"
DEFAULT_OUT_DIR = "docs/evidence/s29-01"
DEFAULT_CANARY_OPS = "docs/evidence/s27-01/provider_canary_ops_latest.json"
DEFAULT_HISTORY = "docs/evidence/s27-01/provider_canary_history.json"
DEFAULT_RECOVERY_CMD = "python3 scripts/ops/s27_provider_canary_ops.py --strict-provider-env"
DEFAULT_ROLLBACK_CMD = "python3 scripts/ops/s25_langchain_poc.py --mode rollback-only"

REASON_INPUT_MISSING = "INPUT_MISSING"
REASON_RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
REASON_RECOVERY_COMMAND_FAILED = "RECOVERY_COMMAND_FAILED"
REASON_SKIP_RATE_HIGH = "SKIP_RATE_HIGH"
REASON_SKIP_RATE_HIGH_ENV_GAP = "SKIP_RATE_HIGH_ENV_GAP"
REASON_RECOVERY_SUCCESS_RATE_HARD_BREACH = "RECOVERY_SUCCESS_RATE_HARD_BREACH"
REASON_RECOVERY_SUCCESS_RATE_SOFT_WARN = "RECOVERY_SUCCESS_RATE_SOFT_WARN"
REASON_RECOVERY_SUCCESS_RATE_INSUFFICIENT_SAMPLE = "RECOVERY_SUCCESS_RATE_INSUFFICIENT_SAMPLE"

SKIP_CAUSE_ENV = "env"
SKIP_CAUSE_CONFIG = "config"
SKIP_CAUSE_RUNTIME = "runtime"
SKIP_CAUSE_UNKNOWN = "unknown"

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(token\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]+)"),
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


def read_toml_if_exists(path: Path) -> Dict[str, Any]:
    if tomllib is None or not path.exists():
        return {}
    try:
        obj = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def trailing_nonpass_streak(runs: List[Dict[str, Any]]) -> int:
    streak = 0
    for row in reversed(runs):
        st = str(row.get("status") or "").upper()
        if st in {"PASS"}:
            break
        streak += 1
    return streak


def classify_skip_reason(reason_code: str) -> str:
    code = str(reason_code or "").upper()
    if not code:
        return SKIP_CAUSE_UNKNOWN
    if "ENV" in code or "CREDENTIAL" in code or "API_KEY" in code:
        return SKIP_CAUSE_ENV
    if "CONFIG" in code or "SCHEMA" in code or "POLICY" in code:
        return SKIP_CAUSE_CONFIG
    if "TIMEOUT" in code or "NETWORK" in code or "HTTP" in code:
        return SKIP_CAUSE_RUNTIME
    return SKIP_CAUSE_UNKNOWN


def summarize_skip_causes(runs: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        SKIP_CAUSE_ENV: 0,
        SKIP_CAUSE_CONFIG: 0,
        SKIP_CAUSE_RUNTIME: 0,
        SKIP_CAUSE_UNKNOWN: 0,
    }
    for row in runs:
        if str(row.get("status") or "").upper() != "SKIP":
            continue
        cause = classify_skip_reason(str(row.get("reason_code") or ""))
        counts[cause] = int(counts.get(cause, 0)) + 1
    return counts


def env_skip_metrics(runs: List[Dict[str, Any]]) -> Dict[str, float | int]:
    skip_runs = [row for row in runs if str(row.get("status") or "").upper() == "SKIP"]
    skip_total = len(skip_runs)
    env_skip_runs = sum(
        1
        for row in skip_runs
        if classify_skip_reason(str(row.get("reason_code") or "")) == SKIP_CAUSE_ENV
    )
    env_skip_rate = 0.0 if skip_total == 0 else round(env_skip_runs / float(skip_total), 4)
    return {
        "skip_total": skip_total,
        "env_skip_runs": env_skip_runs,
        "env_skip_rate": env_skip_rate,
    }


def dominant_cause(counts: Dict[str, int]) -> str:
    rows = sorted(counts.items(), key=lambda x: (-int(x[1]), x[0]))
    if not rows or int(rows[0][1]) <= 0:
        return SKIP_CAUSE_UNKNOWN
    return str(rows[0][0])


def build_recommended_actions(rollback_cmd: str, top_cause: str, trailing: int, recovery_threshold: int) -> List[str]:
    actions: List[str] = []
    if top_cause == SKIP_CAUSE_ENV:
        actions.append("Validate provider env variables (`base_url/api_key/model`) in runtime and CI contexts.")
    elif top_cause == SKIP_CAUSE_CONFIG:
        actions.append("Validate provider canary config/policy file schema and referenced paths.")
    elif top_cause == SKIP_CAUSE_RUNTIME:
        actions.append("Investigate provider/network instability and tune timeout/backoff policy.")
    else:
        actions.append("Inspect latest canary logs and classify dominant skip/fail reason before retry.")

    if trailing >= recovery_threshold:
        actions.append("Run strict canary once and verify status transition to PASS after recovery action.")
    actions.append(f"Keep rollback path ready: {rollback_cmd}")
    return actions


def redact_sensitive_text(text: str, max_len: int = 1200) -> str:
    value = str(text or "")
    for pat in SENSITIVE_PATTERNS:
        value = pat.sub(r"\\1[REDACTED]", value)
    if len(value) > max(1, int(max_len)):
        return value[-max_len:]
    return value


def run_recovery_command(repo_root: Path, command: str, timeout_sec: int, *, include_command_output: bool) -> Dict[str, Any]:
    try:
        cp = subprocess.run(
            shlex.split(command),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_sec)),
            check=False,
        )
    except Exception as exc:
        return {
            "command": command,
            "returncode": 1,
            "status": "FAIL",
            "stdout_tail": "",
            "stderr_tail": redact_sensitive_text(str(exc), max_len=220) if include_command_output else "",
        }
    stdout_tail = redact_sensitive_text(str(cp.stdout or ""), max_len=1200) if include_command_output else ""
    stderr_tail = redact_sensitive_text(str(cp.stderr or ""), max_len=1200) if include_command_output else ""
    return {
        "command": command,
        "returncode": int(cp.returncode),
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _is_nonpass(row: Dict[str, Any]) -> bool:
    return str(row.get("status") or "").upper() in {"FAIL", "SKIP", "WARN"}


def _is_pass(row: Dict[str, Any]) -> bool:
    return str(row.get("status") or "").upper() == "PASS"


def _is_recovery_attempt_row(row: Dict[str, Any]) -> bool:
    if bool(row.get("recovery_attempted")):
        return True
    nested = row.get("recovery")
    if isinstance(nested, dict) and bool(nested.get("attempted")):
        return True
    code = str(row.get("reason_code") or "").upper()
    return "RECOVERY_" in code or "ROLLBACK" in code


def _is_recovery_success_row(row: Dict[str, Any]) -> bool:
    if bool(row.get("recovery_success")):
        return True
    nested = row.get("recovery")
    if isinstance(nested, dict) and str(nested.get("status") or "").upper() == "PASS":
        return True
    status = str(row.get("recovery_status") or "").upper()
    if status == "PASS":
        return True
    code = str(row.get("reason_code") or "").upper()
    return "RECOVERY_SUCCESS" in code or "RECOVERY_OK" in code


def estimate_recovery_success_metrics(runs: List[Dict[str, Any]], runtime_recovery: Dict[str, Any]) -> Dict[str, Any]:
    explicit_attempts = 0
    explicit_successes = 0
    for row in runs:
        if not _is_recovery_attempt_row(row):
            continue
        explicit_attempts += 1
        if _is_recovery_success_row(row):
            explicit_successes += 1

    if explicit_attempts > 0:
        attempts = explicit_attempts
        successes = explicit_successes
        source = "explicit"
    else:
        attempts = 0
        successes = 0
        # Fallback: count non-pass -> next pass transitions as implicit recovery attempts.
        for idx, row in enumerate(runs):
            if not _is_nonpass(row):
                continue
            if idx + 1 >= len(runs):
                continue
            attempts += 1
            if _is_pass(runs[idx + 1]):
                successes += 1
        source = "transition"

    if bool(runtime_recovery.get("attempted")):
        attempts += 1
        if str(runtime_recovery.get("status") or "").upper() == "PASS":
            successes += 1

    success_rate = 1.0 if attempts <= 0 else round(successes / float(attempts), 4)
    return {
        "attempts": attempts,
        "successes": successes,
        "success_rate": success_rate,
        "source": source,
    }


def evaluate_recovery_success_rate_slo(
    *,
    attempts: int,
    success_rate: float,
    soft_threshold: float,
    hard_threshold: float,
    min_attempts_soft: int,
    min_attempts_hard: int,
) -> Dict[str, Any]:
    if attempts < max(0, int(min_attempts_hard)):
        return {
            "level": "INSUFFICIENT_SAMPLE",
            "reason_code": REASON_RECOVERY_SUCCESS_RATE_INSUFFICIENT_SAMPLE,
            "violated": True,
        }
    if attempts < max(0, int(min_attempts_soft)):
        return {
            "level": "SOFT_WARN",
            "reason_code": REASON_RECOVERY_SUCCESS_RATE_INSUFFICIENT_SAMPLE,
            "violated": True,
        }
    if success_rate < float(hard_threshold):
        return {
            "level": "HARD_BREACH",
            "reason_code": REASON_RECOVERY_SUCCESS_RATE_HARD_BREACH,
            "violated": True,
        }
    if success_rate < float(soft_threshold):
        return {
            "level": "SOFT_WARN",
            "reason_code": REASON_RECOVERY_SUCCESS_RATE_SOFT_WARN,
            "violated": True,
        }
    return {"level": "PASS", "reason_code": "", "violated": False}


def build_exit_conditions(
    *,
    reason_code: str,
    recovery_threshold: int,
    skip_rate_warn_threshold: float,
    success_rate_soft_threshold: float,
    min_attempts_soft: int,
) -> List[str]:
    code = str(reason_code or "")
    if code == REASON_INPUT_MISSING:
        return ["Restore canary ops/history artifacts and rerun S29-01."]
    if code == REASON_RECOVERY_REQUIRED:
        return [f"Keep trailing non-pass streak below {max(1, int(recovery_threshold))}."]
    if code in {REASON_SKIP_RATE_HIGH, REASON_SKIP_RATE_HIGH_ENV_GAP}:
        return [f"Reduce skip_rate below {float(skip_rate_warn_threshold):.2f} within configured window."]
    if code in {
        REASON_RECOVERY_SUCCESS_RATE_SOFT_WARN,
        REASON_RECOVERY_SUCCESS_RATE_HARD_BREACH,
        REASON_RECOVERY_SUCCESS_RATE_INSUFFICIENT_SAMPLE,
    }:
        return [
            f"Reach recovery_success_rate >= {float(success_rate_soft_threshold):.2f}.",
            f"Collect at least {max(1, int(min_attempts_soft))} recovery attempts.",
        ]
    if code == REASON_RECOVERY_COMMAND_FAILED:
        return ["Fix recovery command failure and confirm PASS return code."]
    return []


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    trend = dict(payload.get("trend", {}))
    recovery_slo = dict(payload.get("recovery_slo", {}))
    lines: List[str] = []
    lines.append("# S29-01 Canary Recovery Success-rate SLO v2 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- trailing_nonpass_streak: `{trend.get('trailing_nonpass_streak', 0)}`")
    lines.append(f"- skip_rate: `{trend.get('skip_rate', 0.0)}`")
    lines.append(f"- recovery_success_rate: `{recovery_slo.get('success_rate', 0.0)}`")
    lines.append(f"- recovery_attempts: `{recovery_slo.get('attempts', 0)}`")
    lines.append(f"- recovery_slo_level: `{recovery_slo.get('level', '')}`")
    lines.append("")
    lines.append("## Recommended Actions")
    lines.append("")
    for item in list(payload.get("recommended_actions", [])):
        lines.append(f"- {item}")
    if not payload.get("recommended_actions"):
        lines.append("- none")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S29-01 Canary Recovery Success-rate SLO v2")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- trailing_nonpass_streak: {trend.get('trailing_nonpass_streak', 0)}")
    lines.append(f"- skip_rate: {trend.get('skip_rate', 0.0)}")
    lines.append(f"- recovery_success_rate: {recovery_slo.get('success_rate', 0.0)}")
    lines.append(f"- recovery_attempts: {recovery_slo.get('attempts', 0)}")
    lines.append(f"- artifact: docs/evidence/s29-01/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--canary-ops-json", default=DEFAULT_CANARY_OPS)
    parser.add_argument("--history-json", default=DEFAULT_HISTORY)
    parser.add_argument("--window-size", type=int, default=6)
    parser.add_argument("--recovery-threshold", type=int, default=3)
    parser.add_argument("--skip-rate-warn-threshold", type=float, default=0.5)
    parser.add_argument("--recovery-cmd", default=DEFAULT_RECOVERY_CMD)
    parser.add_argument("--rollback-cmd", default=DEFAULT_ROLLBACK_CMD)
    parser.add_argument("--recovery-timeout-sec", type=int, default=300)
    parser.add_argument("--allow-recovery-exec", action="store_true")
    parser.add_argument("--include-command-output", action="store_true")
    parser.add_argument("--success-rate-soft-threshold", type=float, default=0.8)
    parser.add_argument("--success-rate-hard-threshold", type=float, default=0.5)
    parser.add_argument("--success-rate-min-attempts-soft", type=int, default=3)
    parser.add_argument("--success-rate-min-attempts-hard", type=int, default=1)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s29-canary-recovery-success-rate-slo", obs_root=args.obs_root)

    cfg_path = (repo_root / str(args.config)).resolve()
    cfg = read_toml_if_exists(cfg_path)
    if cfg_path.exists() and not cfg:
        emit("WARN", f"config parse failed path={cfg_path}; fallback to cli args", events)

    canary_ops_rel = str(cfg.get("canary_ops_json", args.canary_ops_json) or args.canary_ops_json)
    history_rel = str(cfg.get("history_json", args.history_json) or args.history_json)
    window = max(1, int(cfg.get("window_size", args.window_size)))
    recovery_threshold = int(cfg.get("recovery_threshold", args.recovery_threshold))
    skip_rate_warn_threshold = float(cfg.get("skip_rate_warn_threshold", args.skip_rate_warn_threshold))
    recovery_cmd = str(cfg.get("recovery_cmd", args.recovery_cmd) or args.recovery_cmd)
    rollback_cfg = str(cfg.get("rollback_cmd", args.rollback_cmd) or args.rollback_cmd)
    success_rate_soft_threshold = float(cfg.get("success_rate_soft_threshold", args.success_rate_soft_threshold))
    success_rate_hard_threshold = float(cfg.get("success_rate_hard_threshold", args.success_rate_hard_threshold))
    success_rate_min_attempts_soft = int(cfg.get("success_rate_min_attempts_soft", args.success_rate_min_attempts_soft))
    success_rate_min_attempts_hard = int(cfg.get("success_rate_min_attempts_hard", args.success_rate_min_attempts_hard))

    canary_ops_path = (repo_root / canary_ops_rel).resolve()
    history_path = (repo_root / history_rel).resolve()
    canary_ops = read_json_if_exists(canary_ops_path)
    history_doc = read_json_if_exists(history_path)
    runs = list(history_doc.get("runs", [])) if isinstance(history_doc.get("runs"), list) else []

    missing_inputs: List[str] = []
    if not canary_ops:
        missing_inputs.append("canary_ops_json")
    if not history_doc:
        missing_inputs.append("history_json")

    trend_src = dict(canary_ops.get("trend", {}))
    sample = runs[-window:]
    total = len(sample)
    skip_runs = sum(1 for x in sample if str(x.get("status") or "").upper() == "SKIP")
    fail_runs = sum(1 for x in sample if str(x.get("status") or "").upper() == "FAIL")
    skip_rate = 0.0 if total == 0 else round(skip_runs / float(total), 4)
    fail_rate = 0.0 if total == 0 else round(fail_runs / float(total), 4)
    trailing = trailing_nonpass_streak(runs)

    rollback_cmd = rollback_cfg
    base_summary = dict(dict(canary_ops.get("base", {})).get("summary", {}))
    if not rollback_cmd:
        rollback_cmd = str(base_summary.get("rollback_command") or DEFAULT_ROLLBACK_CMD)

    skip_cause_counts = summarize_skip_causes(sample)
    env_metrics = env_skip_metrics(sample)
    top_cause = dominant_cause(skip_cause_counts)
    env_gap_detected = bool(top_cause == SKIP_CAUSE_ENV and float(env_metrics.get("env_skip_rate", 0.0)) >= 0.8)
    recommended_actions = build_recommended_actions(
        rollback_cmd=rollback_cmd,
        top_cause=top_cause,
        trailing=trailing,
        recovery_threshold=recovery_threshold,
    )

    recovery_exec: Dict[str, Any] = {
        "attempted": False,
        "command": recovery_cmd,
        "returncode": 0,
        "status": "SKIP",
        "stdout_tail": "",
        "stderr_tail": "",
    }

    status = "PASS"
    reason_code = ""
    if missing_inputs:
        status = "WARN"
        reason_code = REASON_INPUT_MISSING
        for name in missing_inputs:
            emit("WARN", f"missing input={name}", events)
    elif trailing >= recovery_threshold:
        status = "WARN"
        reason_code = REASON_RECOVERY_REQUIRED
        emit("WARN", f"recovery required trailing_nonpass_streak={trailing}", events)
        if args.allow_recovery_exec:
            recovery_exec = run_recovery_command(
                repo_root,
                recovery_cmd,
                int(args.recovery_timeout_sec),
                include_command_output=bool(args.include_command_output),
            )
            recovery_exec["attempted"] = True
            if recovery_exec.get("status") != "PASS":
                status = "FAIL"
                reason_code = REASON_RECOVERY_COMMAND_FAILED
            else:
                status = "WARN"
                reason_code = REASON_RECOVERY_REQUIRED
            level = "OK" if recovery_exec.get("status") == "PASS" else "ERROR"
            emit(level, f"recovery exec status={recovery_exec.get('status')} rc={recovery_exec.get('returncode')}", events)
    elif float(trend_src.get("skip_rate", skip_rate)) > skip_rate_warn_threshold:
        status = "WARN"
        reason_code = REASON_SKIP_RATE_HIGH_ENV_GAP if env_gap_detected else REASON_SKIP_RATE_HIGH
        emit("WARN", f"skip rate high skip_rate={trend_src.get('skip_rate', skip_rate)}", events)
    else:
        emit("OK", "recovery strategy status=PASS", events)

    if status == "FAIL":
        emit("ERROR", f"recovery strategy FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"recovery strategy WARN reason={reason_code}", events)

    recovery_slo_metrics = estimate_recovery_success_metrics(sample, recovery_exec)
    recovery_slo_eval = evaluate_recovery_success_rate_slo(
        attempts=int(recovery_slo_metrics.get("attempts", 0)),
        success_rate=float(recovery_slo_metrics.get("success_rate", 0.0)),
        soft_threshold=success_rate_soft_threshold,
        hard_threshold=success_rate_hard_threshold,
        min_attempts_soft=success_rate_min_attempts_soft,
        min_attempts_hard=success_rate_min_attempts_hard,
    )
    recovery_slo = {
        **recovery_slo_metrics,
        **recovery_slo_eval,
        "thresholds": {
            "soft": success_rate_soft_threshold,
            "hard": success_rate_hard_threshold,
            "min_attempts_soft": max(0, success_rate_min_attempts_soft),
            "min_attempts_hard": max(0, success_rate_min_attempts_hard),
        },
    }
    if recovery_slo["level"] == "HARD_BREACH":
        emit(
            "ERROR",
            f"recovery success-rate hard breach rate={recovery_slo['success_rate']} attempts={recovery_slo['attempts']}",
            events,
        )
        if status != "FAIL":
            status = "FAIL"
            reason_code = str(recovery_slo["reason_code"])
    elif recovery_slo["level"] in {"SOFT_WARN", "INSUFFICIENT_SAMPLE"}:
        emit(
            "WARN",
            f"recovery success-rate warn level={recovery_slo['level']} rate={recovery_slo['success_rate']} attempts={recovery_slo['attempts']}",
            events,
        )
        if status == "PASS":
            status = "WARN"
            reason_code = str(recovery_slo["reason_code"])
    else:
        emit(
            "OK",
            f"recovery success-rate pass rate={recovery_slo['success_rate']} attempts={recovery_slo['attempts']}",
            events,
        )

    if recovery_slo["level"] != "PASS":
        recommended_actions.append(
            "Improve canary auto-recovery success-rate via strict retry/rollback validation and provider env hardening."
        )

    exit_conditions = build_exit_conditions(
        reason_code=reason_code,
        recovery_threshold=recovery_threshold,
        skip_rate_warn_threshold=skip_rate_warn_threshold,
        success_rate_soft_threshold=success_rate_soft_threshold,
        min_attempts_soft=success_rate_min_attempts_soft,
    )

    payload: Dict[str, Any] = {
        "schema_version": "s29-canary-recovery-success-rate-slo-v2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "canary_ops_json": to_repo_rel(repo_root, canary_ops_path),
            "history_json": to_repo_rel(repo_root, history_path),
            "config": to_repo_rel(repo_root, cfg_path),
            "window_size": window,
            "recovery_threshold": recovery_threshold,
            "skip_rate_warn_threshold": skip_rate_warn_threshold,
            "success_rate_soft_threshold": success_rate_soft_threshold,
            "success_rate_hard_threshold": success_rate_hard_threshold,
            "success_rate_min_attempts_soft": success_rate_min_attempts_soft,
            "success_rate_min_attempts_hard": success_rate_min_attempts_hard,
            "include_command_output": bool(args.include_command_output),
        },
        "trend": {
            "window_count": total,
            "skip_runs": skip_runs,
            "fail_runs": fail_runs,
            "skip_rate": skip_rate,
            "fail_rate": fail_rate,
            "trailing_nonpass_streak": trailing,
            "base_skip_rate": float(trend_src.get("skip_rate", 0.0) or 0.0),
            "skip_cause_counts": skip_cause_counts,
            "dominant_skip_cause": top_cause,
            "env_skip_runs": int(env_metrics.get("env_skip_runs", 0)),
            "env_skip_rate": float(env_metrics.get("env_skip_rate", 0.0)),
        },
        "recovery": recovery_exec,
        "recovery_slo": recovery_slo,
        "recommended_actions": recommended_actions,
        "constraints": {
            "exit_conditions": exit_conditions,
        },
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "missing_inputs": len(missing_inputs),
            "dominant_skip_cause": top_cause,
            "env_gap_detected": env_gap_detected,
            "recovery_success_rate": float(recovery_slo.get("success_rate", 0.0)),
            "recovery_slo_level": str(recovery_slo.get("level", "")),
            "exit_condition_count": len(exit_conditions),
        },
        "artifact_names": {
            "json": "canary_recovery_success_rate_slo_latest.json",
            "md": "canary_recovery_success_rate_slo_latest.md",
        },
    }

    out_json = out_dir / "canary_recovery_success_rate_slo_latest.json"
    out_md = out_dir / "canary_recovery_success_rate_slo_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
