#!/usr/bin/env python3
"""Decide verify-pack cost scope from policy (lite/balanced/full)."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional


ZERO_SHA = "0000000000000000000000000000000000000000"


def _single_line(value: object) -> str:
    s = str(value).replace("\r", "\n")
    parts = [x.strip() for x in s.split("\n") if x.strip()]
    return " | ".join(parts)


def _run_git_diff(base: str, head: str) -> Optional[List[str]]:
    if not base or not head or base == ZERO_SHA:
        return None
    try:
        cp = subprocess.run(
            ["git", "diff", "--name-status", "--no-renames", "-z", base, head],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception:
        return None
    if cp.returncode != 0:
        return None
    raw = cp.stdout or b""
    if not isinstance(raw, (bytes, bytearray)):
        return None
    parts = bytes(raw).split(b"\0")
    changed: List[str] = []
    i = 0
    while i + 1 < len(parts):
        status = parts[i].decode("utf-8", errors="replace").strip()
        path = parts[i + 1].decode("utf-8", errors="replace").strip()
        i += 2
        if not status or not path:
            continue
        changed.append(path)
    return changed


def _load_policy(path: str) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("policy must be object")
    return obj


def _match_any(path: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
    return False


def decide(
    policy: Dict[str, object],
    event_name: str,
    git_ref: str,
    mode_input: str,
    changed_files: Optional[List[str]],
) -> Dict[str, object]:
    default_mode = str(policy.get("default_mode") or "balanced").strip() or "balanced"
    modes = policy.get("modes")
    if not isinstance(modes, dict):
        modes = {}
    patterns = policy.get("docs_only_allowlist_globs")
    if not isinstance(patterns, list):
        patterns = []
    patterns = [str(p).strip() for p in patterns if str(p).strip()]

    force_heavy = policy.get("force_heavy")
    force_events: List[str] = []
    force_refs: List[str] = []
    if isinstance(force_heavy, dict):
        raw_events = force_heavy.get("events")
        raw_refs = force_heavy.get("refs")
        if isinstance(raw_events, list):
            force_events = [str(x).strip() for x in raw_events if str(x).strip()]
        if isinstance(raw_refs, list):
            force_refs = [str(x).strip() for x in raw_refs if str(x).strip()]

    mode_requested = mode_input.strip() if mode_input else ""
    mode = mode_requested or default_mode
    fallback = False
    if mode not in modes:
        mode = default_mode
        fallback = True

    reason_prefix = ""
    if fallback:
        reason_prefix = f"fallback_mode:{mode_requested or 'empty'};"

    if event_name in force_events:
        return {
            "mode": mode,
            "heavy_needed": 1,
            "reason": reason_prefix + f"force_event:{event_name}",
            "changed_count": len(changed_files or []),
        }
    if git_ref in force_refs:
        return {
            "mode": mode,
            "heavy_needed": 1,
            "reason": reason_prefix + f"force_ref:{git_ref}",
            "changed_count": len(changed_files or []),
        }

    mode_cfg = modes.get(mode)
    strategy = ""
    if isinstance(mode_cfg, dict):
        strategy = str(mode_cfg.get("strategy") or "").strip()

    if strategy == "always_heavy":
        return {
            "mode": mode,
            "heavy_needed": 1,
            "reason": reason_prefix + "mode_always_heavy",
            "changed_count": len(changed_files or []),
        }
    if strategy == "always_light":
        return {
            "mode": mode,
            "heavy_needed": 0,
            "reason": reason_prefix + "mode_always_light",
            "changed_count": len(changed_files or []),
        }
    if strategy != "docs_only_light":
        return {
            "mode": mode,
            "heavy_needed": 1,
            "reason": reason_prefix + f"invalid_strategy:{strategy or 'empty'}",
            "changed_count": len(changed_files or []),
        }

    if changed_files is None:
        return {
            "mode": mode,
            "heavy_needed": 1,
            "reason": reason_prefix + "missing_change_list",
            "changed_count": 0,
        }
    if not changed_files:
        return {
            "mode": mode,
            "heavy_needed": 0,
            "reason": reason_prefix + "empty_diff",
            "changed_count": 0,
        }

    for path in changed_files:
        if not _match_any(path, patterns):
            return {
                "mode": mode,
                "heavy_needed": 1,
                "reason": reason_prefix + f"impact_file:{path}",
                "changed_count": len(changed_files),
            }

    return {
        "mode": mode,
        "heavy_needed": 0,
        "reason": reason_prefix + "docs_only",
        "changed_count": len(changed_files),
    }


def _write_outputs(path: str, decision: Dict[str, object]) -> None:
    if not path:
        return
    mode = _single_line(decision.get("mode", "")) or "balanced"
    reason = _single_line(decision.get("reason", ""))
    try:
        heavy_needed = int(decision.get("heavy_needed", 1))
    except Exception:
        heavy_needed = 1
    try:
        changed_count = int(decision.get("changed_count", 0))
    except Exception:
        changed_count = 0
    lines = [
        f"mode={mode}",
        f"heavy_needed={heavy_needed}",
        f"reason={reason}",
        f"changed_count={changed_count}",
    ]
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Decide CI cost scope")
    p.add_argument("--policy", default="ops/ci/cost_scope_policy.json")
    p.add_argument("--event", default="")
    p.add_argument("--ref", default="")
    p.add_argument("--base", default="")
    p.add_argument("--head", default="")
    p.add_argument("--mode", default="")
    p.add_argument("--changed-file", action="append", default=[])
    p.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    ns = parse_args(argv)

    decision: Dict[str, object]
    try:
        policy = _load_policy(ns.policy)

        changed_files: Optional[List[str]] = None
        if ns.changed_file:
            changed_files = [x for x in ns.changed_file if x]
        else:
            changed_files = _run_git_diff(ns.base, ns.head)

        decision = decide(
            policy=policy,
            event_name=str(ns.event or "").strip(),
            git_ref=str(ns.ref or "").strip(),
            mode_input=str(ns.mode or "").strip(),
            changed_files=changed_files,
        )
    except Exception as exc:
        mode_fallback = str(ns.mode or "").strip() or "balanced"
        decision = {
            "mode": mode_fallback,
            "heavy_needed": 1,
            "reason": _single_line(f"decider_error:{exc}"),
            "changed_count": 0,
        }

    decision["mode"] = _single_line(decision.get("mode", "")) or "balanced"
    decision["reason"] = _single_line(decision.get("reason", ""))
    _write_outputs(ns.github_output, decision)
    if ns.json:
        print(json.dumps(decision, ensure_ascii=True, sort_keys=True))
    else:
        reason = str(decision.get("reason", ""))
        prefix = "ERROR" if reason.startswith("decider_error:") else "OK"
        print(
            f"{prefix}: cost_scope "
            f"mode={decision['mode']} heavy_needed={decision['heavy_needed']} "
            f"reason={decision['reason']} changed_count={decision['changed_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
