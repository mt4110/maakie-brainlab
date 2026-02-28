#!/usr/bin/env python3
"""
S32-21: IL opcode catalog generator.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src import il_executor  # noqa: E402


def _type_name(tp: Any) -> str:
    name = getattr(tp, "__name__", "")
    return name or str(tp)


def build_catalog(exec_contract_text: str) -> Dict[str, Any]:
    args_spec = dict(getattr(il_executor, "OPCODE_ARGS_SPEC", {}))
    handlers = dict(getattr(il_executor, "_OPCODE_HANDLERS", {}))

    opcodes = sorted(set(args_spec.keys()) | set(handlers.keys()))
    rows: List[Dict[str, Any]] = []
    undocumented: List[str] = []
    no_handler: List[str] = []

    for op in opcodes:
        spec = dict(args_spec.get(op, {}))
        args = [{"name": key, "type": _type_name(val)} for key, val in sorted(spec.items(), key=lambda kv: kv[0])]
        has_handler = op in handlers
        documented = op in exec_contract_text
        if not documented:
            undocumented.append(op)
        if not has_handler:
            no_handler.append(op)
        rows.append(
            {
                "opcode": op,
                "args": args,
                "arg_count": len(args),
                "has_handler": has_handler,
                "documented_in_exec_contract": documented,
            }
        )

    status = "PASS" if not undocumented and not no_handler else "WARN"
    return {
        "schema": "S32_OPCODE_CATALOG_V1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "summary": {
            "opcode_count": len(rows),
            "undocumented_count": len(undocumented),
            "missing_handler_count": len(no_handler),
        },
        "undocumented_opcodes": undocumented,
        "missing_handler_opcodes": no_handler,
        "opcodes": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/il")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (repo_root / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    exec_contract = (repo_root / "docs" / "il" / "IL_EXEC_CONTRACT_v1.md").read_text(encoding="utf-8")
    catalog = build_catalog(exec_contract)

    (out_dir / "opcode_catalog_latest.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    md_lines = [
        "# IL Opcode Catalog (Latest)",
        "",
        f"- status: `{catalog['status']}`",
        f"- opcode_count: `{catalog['summary']['opcode_count']}`",
        f"- undocumented_count: `{catalog['summary']['undocumented_count']}`",
        f"- missing_handler_count: `{catalog['summary']['missing_handler_count']}`",
        "",
        "| opcode | args | documented | handler |",
        "|---|---|---|---|",
    ]
    for row in catalog["opcodes"]:
        args_text = ", ".join(f"{a['name']}:{a['type']}" for a in row["args"]) or "-"
        md_lines.append(
            "| {op} | {args} | {doc} | {handler} |".format(
                op=row["opcode"],
                args=args_text,
                doc="yes" if row["documented_in_exec_contract"] else "no",
                handler="yes" if row["has_handler"] else "no",
            )
        )
    (out_dir / "opcode_catalog_latest.md").write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    print(
        "OK: s32_opcode_catalog_generator status={status} opcode_count={count}".format(
            status=catalog["status"],
            count=catalog["summary"]["opcode_count"],
        )
    )
    return 0 if catalog["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
