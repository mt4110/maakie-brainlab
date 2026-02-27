#!/usr/bin/env python3
"""
S30 backlog reclassifier.

Goal:
- Reclassify pending checkbox tasks by impact on daily usability.
- Keep ordering focused on:
  1) execute -> verify -> judge failure-point elimination
  2) log/output readability
  3) repetitive operation automation
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s30-01"
DEFAULT_JSON_NAME = "task_reclass_latest.json"
DEFAULT_MD_NAME = "task_reclass_latest.md"
DEFAULT_BATCH_SIZE = 100

CHECKBOX_PENDING_RX = re.compile(r"^\s*-\s*\[ \]\s+(.+?)\s*$")
CHECKBOX_ANY_RX = re.compile(r"^(\s*-\s*)\[( |x|X)\](\s+.+?)\s*$")


@dataclass
class AxisRule:
    axis_id: str
    label: str
    rank: int
    base_score: int
    keywords: Sequence[Tuple[str, int]]


AXIS_RULES: Sequence[AxisRule] = (
    AxisRule(
        axis_id="A_FLOW_FAILZERO",
        label="Daily flow failure zeroing (execute->verify->judge)",
        rank=0,
        base_score=300,
        keywords=(
            ("実行", 3),
            ("execute", 3),
            ("run", 3),
            ("検証", 3),
            ("verify", 3),
            ("test", 2),
            ("判定", 3),
            ("readiness", 2),
            ("gate", 2),
            ("ci-self", 2),
            ("error", 2),
            ("fail", 2),
            ("stop", 2),
            ("guard", 1),
            ("smoke", 1),
        ),
    ),
    AxisRule(
        axis_id="B_LOG_CLARITY",
        label="Log/output clarity (instant understanding)",
        rank=1,
        base_score=200,
        keywords=(
            ("ログ", 3),
            ("log", 3),
            ("出力", 3),
            ("output", 3),
            ("obs", 2),
            ("evidence", 2),
            ("result", 2),
            ("summary", 2),
            ("report", 2),
            ("artifact", 1),
            ("ok:", 1),
            ("error:", 1),
            ("skip:", 1),
            ("sot", 1),
            ("見て", 1),
            ("わか", 1),
        ),
    ),
    AxisRule(
        axis_id="C_AUTOMATION",
        label="Automation of repetitive operations",
        rank=2,
        base_score=100,
        keywords=(
            ("自動", 3),
            ("automation", 3),
            ("script", 2),
            ("workflow", 2),
            ("make ", 2),
            ("template", 2),
            ("テンプレ", 2),
            ("loop", 2),
            ("batch", 2),
            ("反復", 2),
            ("繰り返", 2),
            ("再実行", 2),
            ("1コマンド", 2),
            ("runbook", 1),
            ("定例", 1),
        ),
    ),
)

AXIS_BY_ID: Dict[str, AxisRule] = {rule.axis_id: rule for rule in AXIS_RULES}


@dataclass
class PendingTask:
    file: str
    line: int
    task: str
    axis_id: str = ""
    axis_label: str = ""
    axis_rank: int = 0
    axis_score: int = 0
    priority_score: int = 0


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def discover_source_files(repo_root: Path, include_ptask: bool = True) -> List[Path]:
    source_dirs = [
        repo_root / "docs" / "ops",
        repo_root / "docs" / "rules",
        repo_root / "docs" / "pr_templates",
    ]
    files: List[Path] = []
    for src in source_dirs:
        if not src.exists():
            continue
        files.extend(p for p in src.rglob("*.md") if p.is_file())
    if include_ptask:
        ptask = repo_root / "+PTASK+"
        if ptask.exists() and ptask.is_file():
            files.append(ptask)
    files.sort(key=lambda p: p.as_posix().lower())
    return files


def extract_pending_from_text(file_rel: str, text: str) -> List[PendingTask]:
    out: List[PendingTask] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        m = CHECKBOX_PENDING_RX.match(raw)
        if not m:
            continue
        task = m.group(1).strip()
        if not task:
            continue
        out.append(PendingTask(file=file_rel, line=idx, task=task))
    return out


def collect_pending_tasks(repo_root: Path, include_ptask: bool = True) -> List[PendingTask]:
    out: List[PendingTask] = []
    for path in discover_source_files(repo_root, include_ptask=include_ptask):
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        out.extend(extract_pending_from_text(rel, text))
    return out


def keyword_score(text: str, keywords: Sequence[Tuple[str, int]]) -> int:
    lowered = text.casefold()
    score = 0
    for keyword, weight in keywords:
        key = keyword.casefold()
        if key and key in lowered:
            score += weight
    return score


def classify_task(task: PendingTask) -> PendingTask:
    scores: List[Tuple[AxisRule, int]] = []
    for rule in AXIS_RULES:
        score = keyword_score(task.task, rule.keywords)
        scores.append((rule, score))

    # Stable tie-break by rule rank, then default to axis A if no signal.
    scores.sort(key=lambda it: (-it[1], it[0].rank))
    chosen, raw_score = scores[0]
    if raw_score <= 0:
        chosen = AXIS_RULES[0]
        raw_score = 1

    bonus = 0
    lowered = task.task.casefold()
    if "error" in lowered or "fail" in lowered or "stop" in lowered:
        bonus += 8
    if "verify-only" in lowered or "検証" in lowered:
        bonus += 5
    if "/ops/" in task.file:
        bonus += 2

    task.axis_id = chosen.axis_id
    task.axis_label = chosen.label
    task.axis_rank = chosen.rank
    task.axis_score = raw_score
    task.priority_score = chosen.base_score + (raw_score * 10) + bonus
    return task


def classify_all(tasks: Iterable[PendingTask]) -> List[PendingTask]:
    out = [classify_task(task) for task in tasks]
    out.sort(key=lambda t: (-t.priority_score, t.axis_rank, t.file, t.line))
    return out


def axis_counts(tasks: Sequence[PendingTask]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {rule.axis_id: 0 for rule in AXIS_RULES}
    for task in tasks:
        counts[task.axis_id] = counts.get(task.axis_id, 0) + 1
    out: List[Dict[str, Any]] = []
    for rule in AXIS_RULES:
        out.append(
            {
                "axis_id": rule.axis_id,
                "label": rule.label,
                "rank": rule.rank,
                "count": counts.get(rule.axis_id, 0),
            }
        )
    return out


def build_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# S30 Task Reclassification (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- Pending total: `{payload.get('summary', {}).get('pending_total', 0)}`")
    lines.append(f"- Batch size: `{payload.get('summary', {}).get('batch_size', 0)}`")
    apply = dict(payload.get("apply", {}))
    if apply.get("enabled"):
        stats = dict(apply.get("stats", {}))
        lines.append(
            "- Apply batch: "
            f"`targeted={stats.get('targeted', 0)} applied={stats.get('applied', 0)} "
            f"already_done={stats.get('already_done', 0)} invalid={stats.get('invalid', 0)}`"
        )
    lines.append("")
    lines.append("## Axis Counts")
    lines.append("")
    for axis in payload.get("axes", []):
        lines.append(f"- `{axis.get('axis_id', '')}`: {axis.get('count', 0)}")
    lines.append("")
    lines.append("## Batch-100 Priority Queue")
    lines.append("")
    for row in payload.get("batch", []):
        lines.append(
            f"{row.get('rank', 0)}. [{row.get('axis_id', '')}] "
            f"`{row.get('file', '')}:{row.get('line', 0)}` - {row.get('task', '')}"
        )
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S30-1-S30-900 Reclass")
    lines.append(f"- pending_total: {payload.get('summary', {}).get('pending_total', 0)}")
    lines.append(f"- batch_size: {payload.get('summary', {}).get('batch_size', 0)}")
    lines.append(
        "- axis_counts: "
        + ", ".join(f"{axis.get('axis_id')}={axis.get('count')}" for axis in payload.get("axes", []))
    )
    lines.append("- artifact: docs/evidence/s30-01/task_reclass_latest.json")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def to_batch_rows(tasks: Sequence[PendingTask], size: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rank, task in enumerate(tasks[:size], start=1):
        row = asdict(task)
        row["rank"] = rank
        rows.append(row)
    return rows


def mark_checked_line(raw: str) -> Tuple[str, bool]:
    m = CHECKBOX_ANY_RX.match(raw.rstrip("\n"))
    if not m:
        return raw, False
    state = m.group(2)
    if state.lower() == "x":
        return raw, False
    replaced = f"{m.group(1)}[x]{m.group(3)}"
    suffix = "\n" if raw.endswith("\n") else ""
    return f"{replaced}{suffix}", True


def apply_batch_rows(repo_root: Path, batch_rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    by_file: Dict[str, List[int]] = {}
    for row in batch_rows:
        file_rel = str(row.get("file", "")).strip()
        line_no = int(row.get("line", 0) or 0)
        if not file_rel or line_no <= 0:
            continue
        by_file.setdefault(file_rel, []).append(line_no)

    stats = {"targeted": len(batch_rows), "applied": 0, "already_done": 0, "invalid": 0}
    for file_rel, line_numbers in by_file.items():
        path = (repo_root / file_rel).resolve()
        root = repo_root.resolve()
        try:
            path.relative_to(root)
        except Exception:
            stats["invalid"] += len(line_numbers)
            continue
        if not path.exists() or not path.is_file():
            stats["invalid"] += len(line_numbers)
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except Exception:
            stats["invalid"] += len(line_numbers)
            continue

        changed = False
        for line_no in sorted(set(line_numbers)):
            if line_no < 1 or line_no > len(lines):
                stats["invalid"] += 1
                continue
            original = lines[line_no - 1]
            pending = CHECKBOX_PENDING_RX.match(original.rstrip("\n"))
            if not pending:
                m = CHECKBOX_ANY_RX.match(original.rstrip("\n"))
                if m and m.group(2).lower() == "x":
                    stats["already_done"] += 1
                else:
                    stats["invalid"] += 1
                continue
            new_line, did = mark_checked_line(original)
            if did:
                lines[line_no - 1] = new_line
                changed = True
                stats["applied"] += 1

        if changed:
            path.write_text("".join(lines), encoding="utf-8")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--no-ptask", action="store_true")
    parser.add_argument("--apply-batch", action="store_true")
    parser.add_argument("--apply-all", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s30-task-reclassify", obs_root=args.obs_root)

    pending = collect_pending_tasks(repo_root, include_ptask=not args.no_ptask)
    if not pending:
        emit("WARN", "no pending checkbox task found", events)

    ranked = classify_all(pending)
    batch_size = max(1, int(args.batch_size or DEFAULT_BATCH_SIZE))
    if args.apply_all:
        batch_size = max(1, len(ranked))
    batch = to_batch_rows(ranked, batch_size)
    apply_stats: Dict[str, int] | None = None

    if (args.apply_batch or args.apply_all) and batch:
        apply_stats = apply_batch_rows(repo_root, batch)
        emit(
            "OK",
            "apply_batch targeted={targeted} applied={applied} already_done={already_done} invalid={invalid}".format(
                **apply_stats
            ),
            events,
        )
        pending = collect_pending_tasks(repo_root, include_ptask=not args.no_ptask)
        ranked = classify_all(pending)
        batch = to_batch_rows(ranked, batch_size)

    axes = axis_counts(ranked)

    payload: Dict[str, Any] = {
        "schema_version": "s30-task-reclass-v1",
        "captured_at_utc": now_utc_iso(),
        "git": {
            "branch": meta.get("branch", ""),
            "head": meta.get("head", ""),
        },
        "inputs": {
            "sources": ["docs/ops/**/*.md", "docs/rules/**/*.md", "docs/pr_templates/**/*.md"]
            + ([] if args.no_ptask else ["+PTASK+"]),
        },
        "summary": {
            "pending_total": len(ranked),
            "batch_size": min(batch_size, len(ranked)),
            "batch_switch_rule": "Switch thread after completing batch tasks.",
        },
        "apply": {"enabled": bool(args.apply_batch or args.apply_all), "stats": apply_stats or {}},
        "axes": axes,
        "batch": batch,
        "all_ranked": [asdict(task) for task in ranked],
        "artifact_names": {"json": DEFAULT_JSON_NAME, "md": DEFAULT_MD_NAME},
    }

    out_json = out_dir / DEFAULT_JSON_NAME
    out_md = out_dir / DEFAULT_MD_NAME
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")

    emit("OK", f"pending_total={len(ranked)}", events)
    for axis in axes:
        emit("OK", f"axis={axis['axis_id']} count={axis['count']}", events)
    emit("OK", f"batch_size={payload['summary']['batch_size']}", events)
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "pending_total": len(ranked),
            "batch_size": payload["summary"]["batch_size"],
            "artifact_json": str(out_json),
            "artifact_md": str(out_md),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
