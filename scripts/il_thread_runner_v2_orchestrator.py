#!/usr/bin/env python3
"""
S32-11: shard orchestrator for il_thread_runner_v2.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.il_thread_runner_v2 import run_thread_runner
from src.il_compile import AUTO_PROMPT_PROFILE, DEFAULT_MODEL, DEFAULT_PROVIDER, normalize_prompt_profile_input


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_orchestrator(
    *,
    cases_path: Path,
    mode: str,
    out_dir: Path,
    shard_count: int,
    provider: str,
    model: str,
    prompt_profile: str,
    seed: int,
    allow_fallback: bool,
    entry_timeout_sec: int,
    entry_retries: int,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    shard_rows: List[Dict[str, Any]] = []
    shard_dirs: List[Path] = []
    for i in range(shard_count):
        shard_dir = out_dir / f"shard_{i:02d}"
        shard_dirs.append(shard_dir)
        rc = run_thread_runner(
            cases_path=cases_path,
            mode=mode,
            out_dir=shard_dir,
            provider=provider,
            model=model,
            prompt_profile=prompt_profile,
            seed=seed,
            allow_fallback=allow_fallback,
            entry_timeout_sec=entry_timeout_sec,
            entry_retries=entry_retries,
            shard_index=i,
            shard_count=shard_count,
        )
        shard_rows.append({"shard_index": i, "shard_dir": str(shard_dir), "returncode": rc})

    merge_dir = out_dir / "merged"
    merge_cmd = [
        "python3",
        str(repo_root / "scripts" / "il_thread_runner_v2_merge.py"),
        "--inputs",
        *[str(x) for x in shard_dirs],
        "--out",
        str(merge_dir),
    ]
    merge_proc = subprocess.run(merge_cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    merge_output = ((merge_proc.stdout or "") + (merge_proc.stderr or "")).strip()

    merged_summary: Dict[str, Any] = {}
    merged_summary_path = merge_dir / "summary.json"
    if merged_summary_path.exists():
        try:
            merged_summary = json.loads(merged_summary_path.read_text(encoding="utf-8"))
        except Exception:
            merged_summary = {}

    shard_failures = sum(1 for row in shard_rows if int(row.get("returncode", 1)) != 0)
    merged_errors = int(merged_summary.get("error_count", 1 if not merged_summary else 0))
    status = "OK" if shard_failures == 0 and merge_proc.returncode == 0 and merged_errors == 0 else "ERROR"
    payload = {
        "schema": "IL_THREAD_RUNNER_V2_ORCHESTRATOR_v1",
        "status": status,
        "mode": mode,
        "cases_path": str(cases_path),
        "out_dir": str(out_dir),
        "shard_count": shard_count,
        "provider": provider,
        "model": model,
        "prompt_profile": prompt_profile,
        "seed": seed,
        "allow_fallback": allow_fallback,
        "entry_timeout_sec": entry_timeout_sec,
        "entry_retries": entry_retries,
        "shards": shard_rows,
        "merge_returncode": merge_proc.returncode,
        "merge_output_tail": merge_output[-600:],
        "merged_summary": merged_summary,
    }
    _write_json(out_dir / "summary.orchestrator.json", payload)

    if status == "OK":
        print(
            "OK: orchestrator_summary status=OK total={total} errors={errors}".format(
                total=merged_summary.get("total_cases", 0),
                errors=merged_summary.get("error_count", 0),
            )
        )
        return 0
    print(
        "ERROR: orchestrator_summary status=ERROR shard_failures={shard_failures} merge_rc={merge_rc} merged_errors={merged_errors}".format(
            shard_failures=shard_failures,
            merge_rc=merge_proc.returncode,
            merged_errors=merged_errors,
        )
    )
    return 1


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--mode", default="validate-only", choices=["validate-only", "run"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--shard-count", type=int, default=2)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-profile", default=AUTO_PROMPT_PROFILE)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-fallback", action="store_true")
    parser.add_argument("--entry-timeout-sec", type=int, default=30)
    parser.add_argument("--entry-retries", type=int, default=0)
    args = parser.parse_args(argv)

    cases_path = Path(args.cases).expanduser()
    if not cases_path.is_absolute():
        cases_path = (repo_root / cases_path).resolve()
    out_dir = Path(args.out).expanduser()
    if not out_dir.is_absolute():
        out_dir = (repo_root / out_dir).resolve()

    shard_count = max(1, int(args.shard_count))
    return run_orchestrator(
        cases_path=cases_path,
        mode=str(args.mode),
        out_dir=out_dir,
        shard_count=shard_count,
        provider=str(args.provider),
        model=str(args.model),
        prompt_profile=normalize_prompt_profile_input(str(args.prompt_profile)),
        seed=int(args.seed),
        allow_fallback=not bool(args.no_fallback),
        entry_timeout_sec=max(1, int(args.entry_timeout_sec)),
        entry_retries=max(0, int(args.entry_retries)),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
