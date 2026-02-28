#!/usr/bin/env python3
"""
S31-24: policy drift guard for IL contracts/scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict


TRACKED = [
    "docs/il/IL_COMPILE_CONTRACT_v1.md",
    "docs/il/IL_EXEC_CONTRACT_v1.md",
    "docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md",
    "scripts/il_compile.py",
    "scripts/il_thread_runner_v2.py",
    "src/il_compile.py",
    "src/il_executor.py",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/evidence/s31-24")
    parser.add_argument("--baseline", default="docs/evidence/s31-24/policy_drift_baseline.json")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    out_dir = (repo_root / args.out_dir).resolve()
    baseline_path = (repo_root / args.baseline).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    current: Dict[str, str] = {}
    missing = []
    for rel in TRACKED:
        path = (repo_root / rel).resolve()
        if not path.exists():
            missing.append(rel)
            continue
        current[rel] = _sha256(path)

    baseline: Dict[str, Any] = {}
    if baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except Exception:
            baseline = {}

    baseline_hashes = dict(baseline.get("hashes", {})) if isinstance(baseline, dict) else {}
    changed = []
    for rel, digest in sorted(current.items()):
        if baseline_hashes.get(rel) and baseline_hashes.get(rel) != digest:
            changed.append(rel)

    status = "PASS" if not missing and not changed else "WARN"
    payload = {
        "schema": "S31_POLICY_DRIFT_GUARD_v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "tracked_count": len(TRACKED),
        "missing": missing,
        "changed": changed,
        "hashes": current,
    }

    if args.update_baseline or not baseline_path.exists():
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_payload = {
            "schema": "S31_POLICY_DRIFT_BASELINE_v1",
            "captured_at_utc": payload["captured_at_utc"],
            "hashes": current,
        }
        baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (out_dir / "policy_drift_guard_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "policy_drift_guard_latest.md").write_text(
        "# S31-24 Policy Drift Guard\n\n"
        f"- status: `{status}`\n"
        f"- missing: `{len(missing)}`\n"
        f"- changed: `{len(changed)}`\n",
        encoding="utf-8",
    )

    print(f"OK: s31_policy_drift_guard status={status} missing={len(missing)} changed={len(changed)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
