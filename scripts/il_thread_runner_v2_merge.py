#!/usr/bin/env python3
"""
S31-17: deterministic merge for sharded il_thread_runner_v2 outputs.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, help="Shard run directories")
    parser.add_argument("--out", required=True, help="Merged output directory")
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    for item in args.inputs:
        run_dir = Path(item).expanduser().resolve()
        cases_path = run_dir / "cases.jsonl"
        if not cases_path.exists():
            print(f"ERROR: missing cases.jsonl in shard: {run_dir}")
            return 1
        records.extend(_load_jsonl(cases_path))

    records = sorted(records, key=lambda r: (int(r.get("index", 0)), str(r.get("id", ""))))

    seen = set()
    deduped: List[Dict[str, Any]] = []
    for row in records:
        key = (int(row.get("index", 0)), str(row.get("id", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    cases_text = "\n".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for r in deduped
    )
    if cases_text:
        cases_text += "\n"
    (out_dir / "cases.jsonl").write_text(cases_text, encoding="utf-8")

    compile_ok = sum(1 for r in deduped if r.get("compile_status") == "OK")
    compile_error = sum(1 for r in deduped if r.get("compile_status") == "ERROR")
    compile_skip = sum(1 for r in deduped if r.get("compile_status") == "SKIP")
    entry_ok = sum(1 for r in deduped if r.get("entry_status") == "OK")
    entry_error = sum(1 for r in deduped if r.get("entry_status") == "ERROR")
    entry_skip = sum(1 for r in deduped if r.get("entry_status") == "SKIP")

    summary = {
        "schema": "IL_THREAD_RUNNER_V2_MERGE_v1",
        "total_cases": len(deduped),
        "compile_ok_count": compile_ok,
        "compile_error_count": compile_error,
        "compile_skip_count": compile_skip,
        "entry_ok_count": entry_ok,
        "entry_error_count": entry_error,
        "entry_skip_count": entry_skip,
        "error_count": compile_error + entry_error,
        "sha256_cases_jsonl": _sha256_text(cases_text),
        "inputs": [str(Path(x).expanduser().resolve()) for x in args.inputs],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK: merge_summary total={summary['total_cases']} errors={summary['error_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
