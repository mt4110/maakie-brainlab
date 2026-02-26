#!/usr/bin/env python3
"""
S25-04 observability contract helpers.

Contract:
- Log levels are strictly one of: OK / WARN / ERROR / SKIP
- Run directory naming is fixed:
  .local/obs/s25-ops/<tool>/<tool>__<UTCSTAMP>__<branch>__<sha7>/
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple


LEVELS = ("OK", "WARN", "ERROR", "SKIP")
DEFAULT_OBS_ROOT = ".local/obs/s25-ops"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(now: dt.datetime | None = None) -> str:
    point = now or utc_now()
    return point.strftime("%Y%m%dT%H%M%SZ")


def sanitize_token(raw: str, max_len: int = 48) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not text:
        return "unknown"
    return text[:max_len]


def git_out(repo_root: Path, args: List[str]) -> str:
    try:
        cp = subprocess.run(["git", *args], cwd=str(repo_root), capture_output=True, text=True, check=False)
    except Exception:
        return ""
    if cp.returncode != 0:
        return ""
    return (cp.stdout or "").strip()


def make_run_context(
    repo_root: Path,
    tool: str,
    obs_root: str = DEFAULT_OBS_ROOT,
) -> Tuple[Path, Dict[str, Any], List[Dict[str, Any]]]:
    branch = git_out(repo_root, ["branch", "--show-current"]) or "unknown"
    head = git_out(repo_root, ["rev-parse", "HEAD"]) or "unknown"
    short = head[:7] if len(head) >= 7 else head
    stamp = utc_stamp()
    tool_slug = sanitize_token(tool, max_len=32)
    branch_slug = sanitize_token(branch, max_len=40)
    run_id = f"{tool_slug}__{stamp}__{branch_slug}__{sanitize_token(short, max_len=12)}"
    run_dir = (repo_root / obs_root / tool_slug / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "schema_version": "s25-obs-contract-v1",
        "tool": tool_slug,
        "run_id": run_id,
        "captured_at_utc": utc_now().isoformat(),
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "branch": branch,
        "head": head,
        "levels": list(LEVELS),
    }
    (run_dir / "run.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return run_dir, meta, []


def emit(level: str, message: str, events: List[Dict[str, Any]]) -> None:
    fixed = level if level in LEVELS else "WARN"
    text = message
    if fixed != level:
        text = f"invalid_level={level} {message}"
    line = f"{fixed}: {text}"
    print(line, flush=True)
    events.append(
        {
            "ts_utc": utc_now().isoformat(),
            "level": fixed,
            "message": text,
        }
    )


def write_events(run_dir: Path, events: List[Dict[str, Any]]) -> Path:
    out = run_dir / "events.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return out


def write_summary(
    run_dir: Path,
    meta: Dict[str, Any],
    events: List[Dict[str, Any]],
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    counts = {level: 0 for level in LEVELS}
    for ev in events:
        lv = str(ev.get("level", ""))
        if lv in counts:
            counts[lv] += 1
    summary = {
        "schema_version": "s25-obs-contract-v1",
        "tool": meta.get("tool"),
        "run_id": meta.get("run_id"),
        "run_dir": str(run_dir),
        "captured_at_utc": meta.get("captured_at_utc"),
        "branch": meta.get("branch"),
        "head": meta.get("head"),
        "counts": counts,
        "events_total": len(events),
        "extra": extra or {},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
