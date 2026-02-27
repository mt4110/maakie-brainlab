#!/usr/bin/env python3
"""
S29-05 policy drift guard v4.

Goal:
- Detect drift across S29 operation contracts.
- Keep high-impact file changes explicit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s29-05"
DEFAULT_BASELINE = "policy_drift_baseline_v4.json"

WATCH_FILES = [
    "docs/ops/S29-01_CANARY_RECOVERY_SUCCESS_RATE_SLO.toml",
    "docs/ops/S29-02_TAXONOMY_PIPELINE_INTEGRATION.toml",
    "docs/ops/S29-07_ACCEPTANCE_CASES_V5.json",
    "scripts/ops/s29_slo_readiness_v3.py",
    "scripts/ops/s29_readiness_notify_multichannel.py",
    ".github/workflows/run_always_1h.yml",
    "Makefile",
]
HIGH_IMPACT_FILES = {
    "scripts/ops/s29_slo_readiness_v3.py",
    "scripts/ops/s29_readiness_notify_multichannel.py",
    ".github/workflows/run_always_1h.yml",
    "Makefile",
}

REASON_BASELINE_CREATED = "BASELINE_CREATED"
REASON_BASELINE_BOOTSTRAPPED = "BASELINE_BOOTSTRAPPED"
REASON_DRIFT_DETECTED = "DRIFT_DETECTED"
REASON_HIGH_IMPACT_DRIFT = "HIGH_IMPACT_DRIFT"


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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scan_current(repo_root: Path, rel_paths: List[str]) -> Dict[str, Any]:
    files: Dict[str, Any] = {}
    for rel in rel_paths:
        path = (repo_root / rel).resolve()
        if not path.exists():
            files[rel] = {"present": False, "sha256": "", "size": 0}
            continue
        files[rel] = {
            "present": True,
            "sha256": file_sha256(path),
            "size": int(path.stat().st_size),
        }
    return {"files": files}


def diff_scans(old_scan: Dict[str, Any], new_scan: Dict[str, Any]) -> Dict[str, List[str]]:
    old_files = dict(old_scan.get("files", {}))
    new_files = dict(new_scan.get("files", {}))
    old_keys = set(old_files.keys())
    new_keys = set(new_files.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed: List[str] = []
    for key in sorted(old_keys & new_keys):
        if old_files.get(key) != new_files.get(key):
            changed.append(key)
    return {"added": added, "removed": removed, "changed": changed}


def high_impact_paths(drift: Dict[str, List[str]]) -> List[str]:
    rows = set(drift.get("added", [])) | set(drift.get("removed", [])) | set(drift.get("changed", []))
    return sorted([p for p in rows if p in HIGH_IMPACT_FILES])


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    drift = dict(payload.get("drift", {}))
    lines: List[str] = []
    lines.append("# S29-05 Policy Drift Guard v4 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- drift_total: `{summary.get('drift_total', 0)}`")
    lines.append(f"- high_impact_changes: `{summary.get('high_impact_changes', 0)}`")
    lines.append("")
    lines.append("## Drift")
    lines.append("")
    lines.append(f"- added: `{drift.get('added', [])}`")
    lines.append(f"- removed: `{drift.get('removed', [])}`")
    lines.append(f"- changed: `{drift.get('changed', [])}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--baseline-file", default=DEFAULT_BASELINE)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--fail-on-high-impact", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--bootstrap-baseline", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s29-policy-drift-guard-v4", obs_root=args.obs_root)

    baseline_path = out_dir / str(args.baseline_file)
    current_scan = scan_current(repo_root, WATCH_FILES)
    baseline = read_json_if_exists(baseline_path)

    status = "PASS"
    reason_code = ""
    drift = {"added": [], "removed": [], "changed": []}
    baseline_state = "existing"

    if not baseline:
        baseline_state = "created"
        if args.bootstrap_baseline:
            status = "PASS"
            reason_code = REASON_BASELINE_BOOTSTRAPPED
            baseline_state = "bootstrapped"
            emit("OK", "baseline bootstrapped", events)
        else:
            status = "WARN"
            reason_code = REASON_BASELINE_CREATED
            emit("WARN", "baseline not found; creating baseline", events)
        baseline_doc = {
            "schema_version": "s29-policy-drift-baseline-v4",
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": current_scan.get("files", {}),
        }
        baseline_path.write_text(json.dumps(baseline_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        drift = diff_scans({"files": baseline.get("files", {})}, current_scan)
        drift_total = len(drift["added"]) + len(drift["removed"]) + len(drift["changed"])
        high_impact = high_impact_paths(drift)
        if drift_total > 0:
            status = "WARN"
            reason_code = REASON_DRIFT_DETECTED
            if high_impact:
                reason_code = REASON_HIGH_IMPACT_DRIFT
                if args.fail_on_high_impact:
                    status = "FAIL"
            emit("WARN", f"drift detected total={drift_total} high={len(high_impact)}", events)
        else:
            emit("OK", "no drift detected", events)

        if args.update_baseline:
            new_base = {
                "schema_version": "s29-policy-drift-baseline-v4",
                "created_at_utc": baseline.get("created_at_utc") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "files": current_scan.get("files", {}),
            }
            baseline_path.write_text(json.dumps(new_base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            emit("OK", "baseline updated", events)

    high_impact_changes = high_impact_paths(drift)
    drift_total = len(drift.get("added", [])) + len(drift.get("removed", [])) + len(drift.get("changed", []))

    payload: Dict[str, Any] = {
        "schema_version": "s29-policy-drift-guard-v4",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "watch_files": WATCH_FILES,
            "baseline_file": to_repo_rel(repo_root, baseline_path),
            "fail_on_high_impact": bool(args.fail_on_high_impact),
            "bootstrap_baseline": bool(args.bootstrap_baseline),
        },
        "current": current_scan,
        "drift": drift,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "drift_total": drift_total,
            "high_impact_changes": len(high_impact_changes),
            "high_impact_files": high_impact_changes,
            "baseline_state": baseline_state,
        },
        "artifact_names": {
            "json": "policy_drift_guard_v4_latest.json",
            "md": "policy_drift_guard_v4_latest.md",
            "baseline": str(args.baseline_file),
        },
    }

    out_json = out_dir / "policy_drift_guard_v4_latest.json"
    out_md = out_dir / "policy_drift_guard_v4_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "drift_total": drift_total})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
