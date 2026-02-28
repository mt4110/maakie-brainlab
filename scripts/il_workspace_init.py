#!/usr/bin/env python3
"""
S31-02: IL workspace initializer.

Generates a minimal workspace with deterministic starter files:
- request.sample.json
- cases.sample.jsonl
- README.md
- out/ directory
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


repo_root = Path(__file__).resolve().parent.parent


def usage() -> str:
    return "python3 scripts/il_workspace_init.py --out <dir> [--template <faq|incident|research>] [--force]"


def parse_args(args: List[str]) -> Tuple[Optional[Path], str, bool, List[str], bool]:
    out_dir: Optional[Path] = None
    template = "faq"
    force = False
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return out_dir, template, force, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out_dir = Path(args[i + 1]).expanduser()
            i += 2
        elif token == "--template":
            if i + 1 >= len(args):
                errors.append("missing value for --template")
                i += 1
                continue
            template = str(args[i + 1]).strip().lower()
            i += 2
        elif token == "--force":
            force = True
            i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    if out_dir is None:
        errors.append("missing required --out")
        return out_dir, template, force, errors, False

    if not out_dir.is_absolute():
        out_dir = (repo_root / out_dir).resolve()
    if template not in {"faq", "incident", "research"}:
        errors.append(f"unknown template: {template}")
    return out_dir, template, force, errors, False


def _template_spec(template: str) -> Dict[str, object]:
    specs: Dict[str, Dict[str, object]] = {
        "faq": {
            "case_id": "sample_alpha",
            "request_text": "Find alpha and beta overview in greek docs",
            "keywords": ["alpha", "beta", "greek"],
            "readme_note": "FAQ lookup focused workflow.",
        },
        "incident": {
            "case_id": "incident_timeline",
            "request_text": "Investigate incident timeline and impacted components for service outage",
            "keywords": ["incident", "timeline", "service", "outage"],
            "readme_note": "Incident triage workflow with evidence-first queries.",
        },
        "research": {
            "case_id": "research_summary",
            "request_text": "Research prior art and summarize tradeoffs for retrieval ranking approach",
            "keywords": ["research", "retrieval", "ranking", "tradeoff"],
            "readme_note": "Research exploration workflow with broader evidence collection.",
        },
    }
    return specs.get(template, specs["faq"])


def _request_template(template: str) -> dict:
    spec = _template_spec(template)
    return {
        "schema": "IL_COMPILE_REQUEST_v1",
        "request_text": spec["request_text"],
        "context": {"keywords": spec["keywords"]},
        "constraints": {
            "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
            "forbidden_keys": [],
            "max_steps": 4,
        },
        "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
        "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
    }


def _cases_template() -> str:
    spec = _template_spec("faq")
    row = {
        "id": spec["case_id"],
        "request": _request_template("faq"),
        "fixture_db": "tests/fixtures/il_exec/retrieve_db.json",
    }
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _cases_template_for(template: str) -> str:
    spec = _template_spec(template)
    row = {
        "id": spec["case_id"],
        "request": _request_template(template),
        "fixture_db": "tests/fixtures/il_exec/retrieve_db.json",
    }
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _readme_template(template: str) -> str:
    spec = _template_spec(template)
    return """# IL Workspace (Sample)

## Files
- `request.sample.json`: single compile request sample
- `cases.sample.jsonl`: thread-runner cases sample
- `out/`: recommended output directory

## Quickstart

```bash
python3 scripts/il_compile.py --request <workspace>/request.sample.json --out <workspace>/out/compile
python3 scripts/il_entry.py <workspace>/out/compile/il.compiled.json --out <workspace>/out/entry --fixture-db tests/fixtures/il_exec/retrieve_db.json
python3 scripts/il_thread_runner_v2.py --cases <workspace>/cases.sample.jsonl --mode validate-only --out <workspace>/out/thread
```

## Notes
- Keep paths repo-root relative.
- Use `--force` only when you intentionally want to overwrite sample files.
 - Template: {template}
 - {note}
""".format(template=template, note=spec["readme_note"])


def run_init(out_dir: Path, template: str, force: bool) -> int:
    targets = [
        out_dir / "request.sample.json",
        out_dir / "cases.sample.jsonl",
        out_dir / "README.md",
    ]
    existing = [p for p in targets if p.exists()]
    if existing and not force:
        for path in existing:
            print(f"ERROR: target already exists: {path}")
        print("ERROR: re-run with --force to overwrite")
        return 1

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "out").mkdir(parents=True, exist_ok=True)

        (out_dir / "request.sample.json").write_text(
            json.dumps(_request_template(template), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "cases.sample.jsonl").write_text(_cases_template_for(template), encoding="utf-8")
        (out_dir / "README.md").write_text(_readme_template(template), encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: failed to initialize workspace: {exc}")
        return 1

    print(f"OK: workspace_initialized={out_dir}")
    print("OK: files=request.sample.json,cases.sample.jsonl,README.md")
    print("OK: out_dir=out")
    print(f"OK: template={template}")
    return 0


def main(argv: List[str]) -> int:
    out_dir, template, force, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    if out_dir is None:
        print("ERROR: missing required --out")
        print(f"OK: usage: {usage()}")
        return 1
    return run_init(out_dir=out_dir, template=template, force=force)


if __name__ == "__main__":
    rc = main(sys.argv[1:])
    sys.exit(rc)
