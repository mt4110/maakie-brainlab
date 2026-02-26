#!/usr/bin/env python3
"""Static guard for required checks contract consistency."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


SOT_RE = re.compile(r"<!--\s*required_checks_sot:v1(.*?)-->", re.S)
JOB_ID_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")


def _norm(items: List[str]) -> List[str]:
    xs = sorted({str(x).strip() for x in items if str(x).strip()})
    return xs


def _load_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_docs_sot(path: Path) -> Optional[List[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = SOT_RE.search(text)
    if not m:
        return None
    lines = []
    for raw in m.group(1).splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return _norm(lines)


def _read_ruleset_sot(path: Path) -> Optional[List[str]]:
    obj = _load_json(path)
    if not isinstance(obj, dict):
        return None
    val = obj.get("required_status_checks")
    if not isinstance(val, list):
        return None
    return _norm([str(x) for x in val])


def _read_workflow_jobs(path: Path) -> Optional[Set[str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    in_jobs = False
    jobs: Set[str] = set()
    for line in lines:
        if line.strip() == "jobs:":
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith(" "):
            break
        if in_jobs:
            m = JOB_ID_RE.match(line)
            if m:
                jobs.add(m.group(1))
    return jobs


def _resolve(root: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    return root / p


def _diff(expected: List[str], actual: List[str]) -> str:
    exp = set(expected)
    act = set(actual)
    missing = sorted(exp - act)
    extra = sorted(act - exp)
    return f"missing={missing if missing else 'NONE'} extra={extra if extra else 'NONE'}"


def check_contract(
    repo_root: Path,
    contract_path: Path,
    docs_path: Path,
    ruleset_path: Path,
) -> Tuple[bool, List[str]]:
    logs: List[str] = []
    ok = True

    contract_obj = _load_json(contract_path)
    if not isinstance(contract_obj, dict):
        return False, [f"ERROR: invalid contract json: {contract_path}"]

    req = contract_obj.get("required_contexts")
    ctx_map = contract_obj.get("context_to_workflow_job")
    if not isinstance(req, list) or not isinstance(ctx_map, dict):
        return False, [f"ERROR: invalid contract keys in {contract_path}"]

    required = _norm([str(x) for x in req])
    logs.append(f"OK: contract contexts n={len(required)} {required}")

    docs_sot = _read_docs_sot(docs_path)
    if docs_sot is None:
        ok = False
        logs.append(f"ERROR: docs SOT block missing: {docs_path}")
    else:
        if docs_sot == required:
            logs.append(f"OK: docs SOT matched n={len(docs_sot)}")
        else:
            ok = False
            logs.append(f"ERROR: docs SOT drift {_diff(required, docs_sot)}")

    ruleset_sot = _read_ruleset_sot(ruleset_path)
    if ruleset_sot is None:
        ok = False
        logs.append(f"ERROR: ruleset SOT missing/invalid: {ruleset_path}")
    else:
        if ruleset_sot == required:
            logs.append(f"OK: ruleset SOT matched n={len(ruleset_sot)}")
        else:
            ok = False
            logs.append(f"ERROR: ruleset SOT drift {_diff(required, ruleset_sot)}")

    for ctx in required:
        meta = ctx_map.get(ctx)
        if not isinstance(meta, dict):
            ok = False
            logs.append(f"ERROR: mapping missing for context={ctx}")
            continue
        wf_raw = str(meta.get("workflow") or "").strip()
        job = str(meta.get("job") or "").strip()
        if not wf_raw or not job:
            ok = False
            logs.append(f"ERROR: invalid mapping for context={ctx}")
            continue
        wf_path = _resolve(repo_root, wf_raw)
        jobs = _read_workflow_jobs(wf_path)
        if jobs is None:
            ok = False
            logs.append(f"ERROR: workflow read failed for context={ctx} path={wf_path}")
            continue
        if job not in jobs:
            ok = False
            logs.append(f"ERROR: workflow job missing context={ctx} path={wf_path} job={job}")
            continue
        logs.append(f"OK: workflow mapping context={ctx} path={wf_path} job={job}")

    return ok, logs


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check required checks contract")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--contract", default="ops/ci/required_checks_contract.json")
    p.add_argument("--docs", default="docs/ops/CI_REQUIRED_CHECKS.md")
    p.add_argument("--ruleset", default="ops/ruleset_required_status_checks.json")
    return p.parse_args()


def main() -> int:
    ns = parse_args()
    root = Path(ns.repo_root).resolve()
    ok, logs = check_contract(
        repo_root=root,
        contract_path=_resolve(root, ns.contract),
        docs_path=_resolve(root, ns.docs),
        ruleset_path=_resolve(root, ns.ruleset),
    )
    for line in logs:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
