#!/usr/bin/env python3
"""
S25-07 ML Experiment runner.

Loads a fixed experiment template, runs il_compile_bench, and records:
- template/config/seed snapshot
- benchmark metrics and threshold evaluation
- PR-body friendly evidence artifacts
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_TEMPLATE = "docs/ops/S25-07_ML_EXPERIMENT_TEMPLATE.json"
DEFAULT_OUT_DIR = "docs/evidence/s25-07"
DEFAULT_TIMEOUT_SEC = 600

REASON_TEMPLATE_INVALID = "TEMPLATE_INVALID"
REASON_BENCH_NONZERO = "BENCH_NONZERO"
REASON_BENCH_TIMEOUT = "BENCH_TIMEOUT"
REASON_SUMMARY_MISSING = "SUMMARY_MISSING"
REASON_SUMMARY_SCHEMA_MISMATCH = "SUMMARY_SCHEMA_MISMATCH"
REASON_THRESHOLD_FAILED = "THRESHOLD_FAILED"
REASON_METRIC_MISSING = "METRIC_MISSING"

ALLOWED_OPS = {"==", ">=", "<=", ">", "<"}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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


def sanitize_command_for_payload(cmd: List[str], repo_root: Path) -> List[str]:
    out: List[str] = []
    for token in cmd:
        text = str(token)
        if not text:
            continue
        p = Path(text)
        if p.is_absolute():
            rel = to_repo_rel(repo_root, p)
            out.append(rel or p.name)
        else:
            out.append(text)
    return out


def _metric_by_path(obj: Dict[str, Any], path: str) -> Optional[float]:
    cur: Any = obj
    for part in str(path).split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    if isinstance(cur, (int, float)):
        return float(cur)
    return None


def _eval_op(actual: float, op: str, target: float) -> bool:
    if op == "==":
        return actual == target
    if op == ">=":
        return actual >= target
    if op == "<=":
        return actual <= target
    if op == ">":
        return actual > target
    if op == "<":
        return actual < target
    return False


def load_template(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_template(tpl: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(tpl, dict):
        return False, "template must be object"
    if str(tpl.get("schema_version") or "") != "s25-ml-experiment-template-v1":
        return False, "schema_version mismatch"
    if not isinstance(tpl.get("input"), dict):
        return False, "input missing"
    if not isinstance(tpl.get("config"), dict):
        return False, "config missing"
    eval_cfg = tpl.get("evaluation")
    if not isinstance(eval_cfg, dict):
        return False, "evaluation missing"
    thresholds = eval_cfg.get("thresholds")
    if not isinstance(thresholds, list) or not thresholds:
        return False, "evaluation.thresholds missing"
    for idx, item in enumerate(thresholds, start=1):
        if not isinstance(item, dict):
            return False, f"threshold[{idx}] must be object"
        metric = str(item.get("metric") or "").strip()
        op = str(item.get("op") or "").strip()
        if not metric:
            return False, f"threshold[{idx}] metric missing"
        if op not in ALLOWED_OPS:
            return False, f"threshold[{idx}] op invalid: {op}"
        try:
            float(item.get("value"))
        except Exception:
            return False, f"threshold[{idx}] value invalid"
    return True, ""


def build_bench_cmd(repo_root: Path, run_dir: Path, tpl: Dict[str, Any], seed_override: Optional[int]) -> List[str]:
    cfg = dict(tpl.get("config", {}))
    if seed_override is not None:
        cfg["seed"] = int(seed_override)

    input_cfg = dict(tpl.get("input", {}))
    cases_path = Path(str(input_cfg.get("cases_path") or "")).expanduser()
    if not cases_path.is_absolute():
        cases_path = (repo_root / cases_path).resolve()

    out_dir = run_dir / "ml_bench"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str((repo_root / "scripts" / "il_compile_bench.py").resolve()),
        "--cases",
        str(cases_path),
        "--out",
        str(out_dir),
        "--provider",
        str(cfg.get("provider") or "rule_based"),
        "--model",
        str(cfg.get("model") or "rule_based_v1"),
        "--prompt-profile",
        str(cfg.get("prompt_profile") or "v1"),
        "--seed",
        str(int(cfg.get("seed", 7))),
        "--expand-factor",
        str(int(cfg.get("expand_factor", 0))),
    ]
    if not bool(cfg.get("allow_fallback", True)):
        cmd.append("--no-fallback")
    return cmd


def run_bench(cmd: List[str], repo_root: Path, run_dir: Path, timeout_sec: int, seed: int) -> Dict[str, Any]:
    t0 = utc_now()
    env = dict()
    env.update({"PYTHONHASHSEED": str(seed), "S25_ML_SEED": str(seed)})
    merged_env = dict(**os.environ, **env)
    timed_out = False
    rc = 0
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=max(1, timeout_sec),
            check=False,
            env=merged_env,
        )
        output = (cp.stdout or "") + (cp.stderr or "")
        rc = cp.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = 124
        out = _to_text(exc.stdout) + _to_text(exc.stderr)
        output = out + f"\nERROR: timeout after {max(1, timeout_sec)}s\n"
    t1 = utc_now()
    (run_dir / "01_ml_experiment.log").write_text(output, encoding="utf-8")
    return {
        "rc": rc,
        "duration_sec": round((t1 - t0).total_seconds(), 3),
        "started_at_utc": t0.isoformat(),
        "ended_at_utc": t1.isoformat(),
        "output": output,
        "timed_out": timed_out,
    }


def evaluate_thresholds(summary: Dict[str, Any], thresholds: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    for item in thresholds:
        metric = str(item.get("metric") or "")
        op = str(item.get("op") or "")
        target = float(item.get("value"))
        actual = _metric_by_path(summary, metric)
        if actual is None:
            rows.append(
                {
                    "metric": metric,
                    "op": op,
                    "target": target,
                    "actual": None,
                    "passed": False,
                    "reason_code": REASON_METRIC_MISSING,
                }
            )
            errors.append(f"{metric}: metric missing")
            continue
        passed = _eval_op(actual, op, target)
        rows.append(
            {
                "metric": metric,
                "op": op,
                "target": target,
                "actual": actual,
                "passed": passed,
                "reason_code": "" if passed else REASON_THRESHOLD_FAILED,
            }
        )
        if not passed:
            errors.append(f"{metric}: actual={actual} {op} target={target} failed")
    return rows, errors


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# S25-07 ML Experiment (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload['captured_at_utc']}`")
    lines.append(f"- Branch: `{payload['git']['branch']}`")
    lines.append(f"- HeadSHA: `{payload['git']['head']}`")
    lines.append(f"- ExperimentId: `{payload['experiment']['experiment_id']}`")
    lines.append(f"- Seed: `{payload['experiment']['seed']}`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- Status: `{summary['status']}`")
    lines.append(f"- Duration: `{summary['duration_sec']} sec`")
    lines.append(f"- BenchRC: `{summary['bench_rc']}`")
    lines.append(f"- Failures: `{len(summary['errors'])}`")
    lines.append("")
    lines.append("## Threshold Checks")
    lines.append("")
    for row in payload["threshold_results"]:
        lines.append(
            f"- `{'PASS' if row['passed'] else 'FAIL'}` `{row['metric']}` "
            f"`actual={row['actual']}` `{row['op']} {row['target']}`"
        )
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-07 ML Experiment Loop")
    lines.append(f"- template: docs/ops/S25-07_ML_EXPERIMENT_TEMPLATE.json")
    lines.append(f"- seed: {payload['experiment']['seed']}")
    lines.append(f"- status: {summary['status']}")
    lines.append(f"- duration: {summary['duration_sec']} sec")
    lines.append(f"- failures: {len(summary['errors'])}")
    lines.append(f"- artifact: docs/evidence/s25-07/{payload['artifact_names']['json']}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=DEFAULT_TEMPLATE)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--seed", type=int, default=None, help="Optional seed override")
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="ml-experiment", obs_root=args.obs_root)

    template_path = (repo_root / args.template).resolve()
    if not template_path.exists():
        emit("ERROR", f"template missing path={template_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_TEMPLATE_INVALID})
        return 1

    tpl = load_template(template_path)
    ok_tpl, why = validate_template(tpl)
    if not ok_tpl:
        emit("ERROR", f"template invalid reason={why}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_TEMPLATE_INVALID})
        return 1
    emit("OK", f"template={template_path}", events)

    cmd = build_bench_cmd(repo_root, run_dir, tpl, seed_override=args.seed)
    cmd_for_payload = sanitize_command_for_payload(cmd, repo_root)
    exp_cfg = dict(tpl.get("config", {}))
    seed = int(exp_cfg.get("seed", 7)) if args.seed is None else int(args.seed)
    (run_dir / "experiment.command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
    (run_dir / "experiment.template.snapshot.json").write_text(
        json.dumps(tpl, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    emit("OK", f"run command={' '.join(cmd)}", events)
    run = run_bench(cmd, repo_root=repo_root, run_dir=run_dir, timeout_sec=int(args.timeout_sec), seed=seed)
    emit("OK", f"bench_rc={run['rc']} duration={run['duration_sec']}s", events)

    errors: List[str] = []
    reason_code = ""
    summary_obj: Dict[str, Any] = {}
    bench_summary_path = run_dir / "ml_bench" / "il.compile.bench.summary.json"
    if run["rc"] != 0:
        if bool(run.get("timed_out")):
            reason_code = REASON_BENCH_TIMEOUT
            errors.append("il_compile_bench timed out")
        else:
            reason_code = REASON_BENCH_NONZERO
            errors.append("il_compile_bench returned non-zero")
    if not bench_summary_path.exists():
        reason_code = reason_code or REASON_SUMMARY_MISSING
        errors.append(f"bench summary missing path={bench_summary_path}")
    else:
        summary_obj = json.loads(bench_summary_path.read_text(encoding="utf-8"))
        required_schema = str(tpl.get("evaluation", {}).get("required_summary_schema") or "")
        if required_schema and str(summary_obj.get("schema") or "") != required_schema:
            reason_code = reason_code or REASON_SUMMARY_SCHEMA_MISMATCH
            errors.append(f"summary schema mismatch expected={required_schema} actual={summary_obj.get('schema')}")

    thresholds = list(tpl.get("evaluation", {}).get("thresholds", []))
    threshold_results: List[Dict[str, Any]] = []
    if summary_obj and not errors:
        threshold_results, threshold_errors = evaluate_thresholds(summary_obj, thresholds)
        if threshold_errors:
            reason_code = reason_code or REASON_THRESHOLD_FAILED
            errors.extend(threshold_errors)

    status = "PASS" if not errors else "FAIL"
    for err in errors:
        emit("ERROR", err, events)
    if status == "PASS":
        emit("OK", "ml_experiment thresholds passed", events)
    else:
        emit("WARN", "ml_experiment thresholds failed", events)

    payload: Dict[str, Any] = {
        "schema_version": "s25-ml-experiment-v1",
        "captured_at_utc": utc_now().isoformat(),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "experiment": {
            "experiment_id": str(tpl.get("experiment_id") or ""),
            "template_path": to_repo_rel(repo_root, template_path),
            "seed": seed,
            "command": cmd_for_payload,
            "rerun_command": f"make s25-ml-experiment",
        },
        "bench_summary_path": to_repo_rel(repo_root, bench_summary_path),
        "bench_summary": summary_obj,
        "threshold_results": threshold_results,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "errors": errors,
            "bench_rc": run["rc"],
            "duration_sec": run["duration_sec"],
        },
        "artifact_names": {
            "json": "ml_experiment_latest.json",
            "md": "ml_experiment_latest.md",
            "run_dir": to_repo_rel(repo_root, run_dir),
        },
        "stop": 0 if status == "PASS" else 1,
    }

    out_json = out_dir / "ml_experiment_latest.json"
    out_md = out_dir / "ml_experiment_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"ml_experiment_json={out_json}", events)
    emit("OK", f"ml_experiment_md={out_md}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    if status == "PASS":
        emit("OK", "ml_experiment completed", events)
    else:
        emit("WARN", "ml_experiment completed with failures", events)

    events_path = write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "ml_experiment_json": to_repo_rel(repo_root, out_json),
            "ml_experiment_md": to_repo_rel(repo_root, out_md),
            "status": status,
            "reason_code": reason_code,
        },
    )
    print(f"OK: obs_events={events_path}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
        raise SystemExit(1)
