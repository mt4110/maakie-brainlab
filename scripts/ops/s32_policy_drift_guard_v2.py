#!/usr/bin/env python3
"""
S32-18: policy drift guard v2 for S32 contracts/scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List


TRACKED = [
    "docs/il/IL_COMPILE_CONTRACT_v1.md",
    "docs/il/IL_EXEC_CONTRACT_v1.md",
    "docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md",
    "docs/ops/S32-01-S32-30-THREAD-V1_TASK.md",
    "scripts/il_compile.py",
    "scripts/il_thread_runner_v2.py",
    "scripts/il_thread_runner_v2_orchestrator.py",
    "scripts/ops/s32_retrieval_eval_wall.py",
    "scripts/ops/s32_operator_dashboard_export.py",
    "scripts/ops/s32_latency_slo_guard.py",
    "scripts/ops/s32_acceptance_wall_v6.py",
    "src/il_compile.py",
    "src/il_executor.py",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def scan_current(repo_root: Path, tracked: List[str]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for rel in tracked:
        path = (repo_root / rel).resolve()
        if path.exists():
            hashes[rel] = _sha256(path)
    return dict(sorted(hashes.items(), key=lambda kv: kv[0]))


def diff_hashes(baseline: Dict[str, str], current: Dict[str, str]) -> Dict[str, List[str]]:
    missing: List[str] = []
    changed: List[str] = []
    for rel in sorted(TRACKED):
        if rel not in current:
            missing.append(rel)
            continue
        if rel not in baseline:
            changed.append(rel)
            continue
        if baseline.get(rel) != current.get(rel):
            changed.append(rel)
    return {"missing": missing, "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s32-18")
    parser.add_argument("--baseline", default="docs/evidence/s32-18/policy_drift_baseline_v2.json")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    baseline_path = (repo_root / args.baseline).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    current_hashes = scan_current(repo_root, TRACKED)
    baseline_doc = _read_json(baseline_path)
    baseline_hashes = dict(baseline_doc.get("hashes", {})) if baseline_doc else {}

    diff = diff_hashes(baseline_hashes, current_hashes) if baseline_hashes else {"missing": [], "changed": []}
    status = "PASS" if not diff["missing"] and not diff["changed"] else "WARN"

    payload = {
        "schema": "S32_POLICY_DRIFT_GUARD_V2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "tracked_count": len(TRACKED),
        "missing": diff["missing"],
        "changed": diff["changed"],
        "hashes": current_hashes,
    }

    if args.update_baseline or not baseline_path.exists():
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_payload = {
            "schema": "S32_POLICY_DRIFT_BASELINE_V2",
            "captured_at_utc": payload["captured_at_utc"],
            "hashes": current_hashes,
        }
        baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (out_dir / "policy_drift_guard_v2_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "policy_drift_guard_v2_latest.md").write_text(
        "# S32-18 Policy Drift Guard v2\n\n"
        f"- status: `{status}`\n"
        f"- missing: `{len(diff['missing'])}`\n"
        f"- changed: `{len(diff['changed'])}`\n",
        encoding="utf-8",
    )

    print(
        "OK: s32_policy_drift_guard_v2 status={status} missing={missing} changed={changed}".format(
            status=status,
            missing=len(diff["missing"]),
            changed=len(diff["changed"]),
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
