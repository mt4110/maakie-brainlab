#!/usr/bin/env python3
"""
Print a compact "where am I now?" snapshot for ops threads.

Output is intentionally stopless:
- Emits OK/WARN/ERROR lines.
- Avoids hard exits on recoverable issues.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, make_run_context, write_events, write_summary


THREAD_RX = re.compile(r"([sS]\d{2}-\d{2}-[sS]?\d{2}-\d{2})")
PHASE_RX = re.compile(r"([sS]\d{2}-\d{2})")
PROGRESS_LINE_RX = re.compile(r"^\s*-\s*([A-Za-z0-9\-]+):\s*([0-9]+(?:\.[0-9]+)?)%\s*(.*)$", re.M)
PERCENT_RX = re.compile(r"([0-9]+(?:\.[0-9]+)?)%")
CHECKBOX_RX = re.compile(r"^\s*-\s*\[([xX ])\]\s+(.+?)\s*$", re.M)
VERSION_TASK_RX = re.compile(r"[-_]V([0-9]+)_TASK\.MD$")


def run_git(args: List[str], cwd: Path, events: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    try:
        cp = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)
    except Exception as exc:
        msg = f"git exception args={' '.join(args)} err={exc}"
        if events is None:
            print(f"WARN: {msg}", flush=True)
        else:
            emit("WARN", msg, events)
        return None
    if cp.returncode != 0:
        stderr = (cp.stderr or "").strip()
        if stderr:
            msg = f"git failed args={' '.join(args)} err={stderr}"
            if events is None:
                print(f"WARN: {msg}", flush=True)
            else:
                emit("WARN", msg, events)
        return None
    return (cp.stdout or "").strip()


def normalize_track(raw: str) -> str:
    parts = raw.split("-")
    if parts:
        parts[0] = parts[0].upper()
    if len(parts) >= 3 and parts[2].lower().startswith("s"):
        parts[2] = parts[2].upper()
    return "-".join(parts)


def detect_track(branch: str) -> str:
    m = THREAD_RX.search(branch or "")
    if m:
        return normalize_track(m.group(1))
    m = PHASE_RX.search(branch or "")
    if m:
        return normalize_track(m.group(1))
    return ""


def score_candidate(name_upper: str, track_upper: str) -> Optional[Tuple[int, int, str]]:
    exact = f"{track_upper}_TASK.MD"
    if name_upper == exact:
        return (0, len(name_upper), name_upper)

    pref_dash = f"{track_upper}-"
    pref_under = f"{track_upper}_"
    if name_upper.startswith(pref_dash) or name_upper.startswith(pref_under):
        return (1, len(name_upper), name_upper)

    series = track_upper.split("-", 1)[0]
    if series and name_upper.startswith(series + "-"):
        return (2, len(name_upper), name_upper)
    return None


def extract_task_version(name_upper: str) -> int:
    m = VERSION_TASK_RX.search(name_upper)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def choose_task_file(docs_dir: Path, track: str) -> Optional[Path]:
    files = sorted(docs_dir.glob("*_TASK.md"))
    if not files:
        return None

    if track:
        scored: List[Tuple[Tuple[int, int, int, str], Path]] = []
        track_upper = track.upper()
        for path in files:
            name_upper = path.name.upper()
            score = score_candidate(name_upper, track_upper)
            if score is not None:
                version = extract_task_version(name_upper)
                # For same match class, prefer newer Vn task files.
                scored.append(((score[0], -version, score[1], score[2]), path))
        if scored:
            scored.sort(key=lambda x: x[0])
            return scored[0][1]

    try:
        return max(files, key=lambda p: p.stat().st_mtime)
    except Exception:
        return files[-1]


def parse_task(task_text: str, max_next: int) -> Tuple[str, str, int, int, List[str]]:
    progress = "unknown"
    progress_detail = ""
    m = PROGRESS_LINE_RX.search(task_text)
    if m:
        progress = f"{m.group(2)}%"
        suffix = m.group(3).strip()
        progress_detail = f"{m.group(1)} {suffix}".strip()
    else:
        p = PERCENT_RX.search(task_text)
        if p:
            progress = f"{p.group(1)}%"

    checked = 0
    total = 0
    next_items: List[str] = []
    for mark, text in CHECKBOX_RX.findall(task_text):
        total += 1
        if mark.lower() == "x":
            checked += 1
        elif len(next_items) < max_next:
            next_items.append(text.strip())
    return progress, progress_detail, checked, total, next_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Show current operations point from branch/task docs.")
    parser.add_argument("--repo-root", default="", help="Repo root path. Default: git root or cwd.")
    parser.add_argument("--branch", default="", help="Branch override.")
    parser.add_argument("--task-file", default="", help="TASK markdown path override.")
    parser.add_argument("--max-next", type=int, default=5, help="Max number of next items to print.")
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT, help="Observability root directory.")
    args = parser.parse_args()

    cwd = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()
    if not args.repo_root:
        git_root = run_git(["rev-parse", "--show-toplevel"], cwd)
        if git_root:
            cwd = Path(git_root)

    run_dir, meta, events = make_run_context(cwd, tool="current-point", obs_root=args.obs_root)

    branch = args.branch or run_git(["branch", "--show-current"], cwd, events=events) or ""
    track = detect_track(branch)

    if branch:
        emit("OK", f"branch={branch}", events)
    else:
        emit("WARN", "branch unknown", events)
    if track:
        emit("OK", f"track_hint={track}", events)
    else:
        emit("WARN", "track_hint unresolved from branch", events)

    if args.task_file:
        task_path = Path(args.task_file)
        if not task_path.is_absolute():
            task_path = cwd / task_path
    else:
        task_path = choose_task_file(cwd / "docs" / "ops", track)

    if task_path is None:
        emit("ERROR", "no TASK file found under docs/ops", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={})
        return
    if not task_path.exists():
        emit("ERROR", f"task file missing path={task_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={})
        return

    rel_task = os.path.relpath(task_path, cwd)
    emit("OK", f"task_file={rel_task}", events)

    try:
        text = task_path.read_text(encoding="utf-8")
    except Exception as exc:
        emit("ERROR", f"cannot read task file err={exc}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={})
        return

    progress, detail, checked, total, next_items = parse_task(text, max_next=max(1, args.max_next))
    emit("OK", f"progress={progress}", events)
    if detail:
        emit("OK", f"progress_detail={detail}", events)
    if total > 0:
        emit("OK", f"checklist={checked}/{total}", events)
    else:
        emit("WARN", "checklist not found", events)

    if next_items:
        emit("OK", f"next_items={len(next_items)}", events)
        print("OK: NEXT:")
        for item in next_items:
            print(f"OK: - [ ] {item}")
    else:
        emit("SKIP", "no pending checklist item found", events)
        print("SKIP: NEXT:")
        print("SKIP: - [ ] no pending checklist item found")

    snapshot = {
        "branch": branch,
        "track_hint": track,
        "task_file": rel_task,
        "progress": progress,
        "progress_detail": detail,
        "checklist": {"checked": checked, "total": total},
        "next_items": next_items,
    }
    (run_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    emit("OK", f"obs_run_dir={run_dir}", events)
    events_path = write_events(run_dir, events)
    summary = write_summary(run_dir, meta, events, extra={"snapshot_file": "snapshot.json"})
    print(f"OK: obs_events={events_path}", flush=True)
    print(f"OK: obs_counts={summary['counts']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
        raise SystemExit(1)
