#!/usr/bin/env python3
"""
S28-01 provider canary recovery strategy.

Goal:
- Detect sustained non-pass streaks from canary history.
- Provide deterministic recovery actions and optional auto-recovery execution.
"""

from __future__ import annotations

import argparse
import json
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


DEFAULT_CONFIG = "docs/ops/S28-01_PROVIDER_CANARY_RECOVERY.toml"
DEFAULT_OUT_DIR = "docs/evidence/s28-01"
DEFAULT_CANARY_OPS = "docs/evidence/s27-01/provider_canary_ops_latest.json"
DEFAULT_HISTORY = "docs/evidence/s27-01/provider_canary_history.json"
DEFAULT_RECOVERY_CMD = "python3 scripts/ops/s27_provider_canary_ops.py --strict-provider-env"
DEFAULT_ROLLBACK_CMD = "python3 scripts/ops/s25_langchain_poc.py --mode rollback-only"

REASON_INPUT_MISSING = "INPUT_MISSING"
REASON_RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
REASON_RECOVERY_COMMAND_FAILED = "RECOVERY_COMMAND_FAILED"
REASON_SKIP_RATE_HIGH = "SKIP_RATE_HIGH"


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


def run_recovery_command(repo_root: Path, command: str, timeout_sec: int) -> Dict[str, Any]:
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
            "stderr_tail": str(exc),
        }
    return {
        "command": command,
        "returncode": int(cp.returncode),
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "stdout_tail": str(cp.stdout or "")[-1200:],
        "stderr_tail": str(cp.stderr or "")[-1200:],
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    trend = dict(payload.get("trend", {}))
    lines: List[str] = []
    lines.append("# S28-01 Provider Canary Recovery (Latest)")
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
    lines.append("### S28-01 Provider Canary Recovery")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- trailing_nonpass_streak: {trend.get('trailing_nonpass_streak', 0)}")
    lines.append(f"- skip_rate: {trend.get('skip_rate', 0.0)}")
    lines.append(f"- artifact: docs/evidence/s28-01/{payload.get('artifact_names', {}).get('json', '')}")
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
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s28-provider-canary-recovery", obs_root=args.obs_root)

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

    recommended_actions = [
        "Validate provider env variables and credentials wiring.",
        "Run strict canary once and verify status transition to PASS.",
        f"Keep rollback path ready: {rollback_cmd}",
    ]

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
            recovery_exec = run_recovery_command(repo_root, recovery_cmd, int(args.recovery_timeout_sec))
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
        reason_code = REASON_SKIP_RATE_HIGH
        emit("WARN", f"skip rate high skip_rate={trend_src.get('skip_rate', skip_rate)}", events)
    else:
        emit("OK", "recovery strategy status=PASS", events)

    if status == "FAIL":
        emit("ERROR", f"recovery strategy FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"recovery strategy WARN reason={reason_code}", events)

    payload: Dict[str, Any] = {
        "schema_version": "s28-provider-canary-recovery-v1",
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
        },
        "trend": {
            "window_count": total,
            "skip_runs": skip_runs,
            "fail_runs": fail_runs,
            "skip_rate": skip_rate,
            "fail_rate": fail_rate,
            "trailing_nonpass_streak": trailing,
            "base_skip_rate": float(trend_src.get("skip_rate", 0.0) or 0.0),
        },
        "recovery": recovery_exec,
        "recommended_actions": recommended_actions,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "missing_inputs": len(missing_inputs),
        },
        "artifact_names": {
            "json": "provider_canary_recovery_latest.json",
            "md": "provider_canary_recovery_latest.md",
        },
    }

    out_json = out_dir / "provider_canary_recovery_latest.json"
    out_md = out_dir / "provider_canary_recovery_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
