# scripts/ops/docs_ops_doctor.py
# exit禁止運用: sys.exit / raise / assert を使わない
# 例外は catch して ERROR を print。終了コードで制御しない。

import os
import re
from pathlib import Path

def safe_read(p: Path):
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERROR: cannot read {p} ({e})")
        return None

def main():
    sprint = os.environ.get("SPRINT", "S22-15")

    plan = Path(f"docs/ops/{sprint}_PLAN.md")
    task = Path(f"docs/ops/{sprint}_TASK.md")
    stat = Path("docs/ops/STATUS.md")

    errors = []
    warns = []

    # existence
    for p in [plan, task, stat]:
        if p.exists():
            print(f"OK: exists={p}")
        else:
            errors.append(f"missing file: {p}")

    # read content (light)
    s_task = safe_read(task) if task.exists() else None
    s_stat = safe_read(stat) if stat.exists() else None

    # TASK progress line
    if s_task is not None:
        m = re.search(rf"^\s*{re.escape(sprint)}:\s*([0-9]+%)\s*(.*)$", s_task, re.M)
        if m:
            print(f"OK: task_progress={m.group(1)} {m.group(2).strip()}")
        else:
            warns.append(f"TASK has no progress line like '{sprint}: ...'")

    # STATUS row
    if s_stat is not None:
        # very tolerant: find any table row that starts with | S22-15 |
        row = re.search(rf"^\s*\|\s*{re.escape(sprint)}\s*\|.*\|\s*([^|]+)\|\s*$", s_stat, re.M)
        if row:
            print(f"OK: status_progress={row.group(1).strip()}")
        else:
            warns.append(f"STATUS has no row for {sprint}")

    # report
    for e in errors:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARN: {w}")

    if len(errors) == 0:
        print("OK: docs_ops_doctor finished (no ERROR)")
    else:
        print("WARN: docs_ops_doctor finished (has ERROR; fix recommended)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 最後の砦: 例外でターミナルを落とさない
        print(f"ERROR: unhandled exception ({e})")
        print("WARN: finished with exception (but process kept alive)")
