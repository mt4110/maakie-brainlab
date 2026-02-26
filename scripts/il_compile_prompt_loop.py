"""
S23-03: local_llm prompt improvement loop.

Runs il_compile_bench with multiple prompt profiles and compares:
- fallback_count (primary minimization target)
- objective_score (secondary maximization target)
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

repo_root = Path(__file__).resolve().parent.parent

DEFAULT_PROFILES = ["v1", "strict_json_v2", "contract_json_v3"]


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return (
        "python3 scripts/il_compile_prompt_loop.py "
        "[--cases <jsonl>] [--out <dir>] [--model <name>] "
        "[--profiles <comma_list>] [--seed <int>] [--expand-factor <int>] [--no-fallback]"
    )


def parse_args(args: List[str]) -> Tuple[Path, Path, str, List[str], int, int, bool, List[str], bool]:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_cases = repo_root / "tests" / "fixtures" / "il_compile" / "bench_cases.jsonl"
    default_out = repo_root / ".local" / "obs" / f"il_compile_prompt_loop_{ts}"

    cases = default_cases
    out = default_out
    model = "local_llm_v1"
    profiles = list(DEFAULT_PROFILES)
    seed = 7
    expand_factor = 1
    allow_fallback = True
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return cases, out, model, profiles, seed, expand_factor, allow_fallback, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--cases":
            if i + 1 >= len(args):
                errors.append("missing value for --cases")
                i += 1
                continue
            cases = Path(args[i + 1]).expanduser()
            if not cases.is_absolute():
                cases = (repo_root / cases).resolve()
            i += 2
        elif token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out = Path(args[i + 1]).expanduser()
            if not out.is_absolute():
                out = (repo_root / out).resolve()
            i += 2
        elif token == "--model":
            if i + 1 >= len(args):
                errors.append("missing value for --model")
                i += 1
                continue
            model = args[i + 1]
            i += 2
        elif token == "--profiles":
            if i + 1 >= len(args):
                errors.append("missing value for --profiles")
                i += 1
                continue
            raw = args[i + 1]
            values = [x.strip() for x in raw.split(",") if x.strip()]
            if values:
                profiles = values
            i += 2
        elif token == "--seed":
            if i + 1 >= len(args):
                errors.append("missing value for --seed")
                i += 1
                continue
            raw = args[i + 1]
            try:
                seed = int(raw)
            except Exception:
                errors.append(f"invalid --seed: {raw}")
            i += 2
        elif token == "--expand-factor":
            if i + 1 >= len(args):
                errors.append("missing value for --expand-factor")
                i += 1
                continue
            raw = args[i + 1]
            try:
                expand_factor = int(raw)
            except Exception:
                errors.append(f"invalid --expand-factor: {raw}")
            i += 2
        elif token == "--no-fallback":
            allow_fallback = False
            i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    return cases, out, model, profiles, seed, expand_factor, allow_fallback, errors, False


def _run_profile(
    profile: str,
    cases: Path,
    out_dir: Path,
    model: str,
    seed: int,
    expand_factor: int,
    allow_fallback: bool,
) -> Dict[str, object]:
    profile_out = out_dir / profile
    profile_out.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3",
        str(repo_root / "scripts" / "il_compile_bench.py"),
        "--cases",
        str(cases),
        "--out",
        str(profile_out),
        "--provider",
        "local_llm",
        "--model",
        model,
        "--prompt-profile",
        profile,
        "--seed",
        str(seed),
        "--expand-factor",
        str(expand_factor),
    ]
    if not allow_fallback:
        cmd.append("--no-fallback")

    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if output.strip():
        print(output.rstrip())

    summary_path = profile_out / "il.compile.bench.summary.json"
    if not summary_path.exists():
        return {
            "profile": profile,
            "status": "ERROR",
            "returncode": proc.returncode,
            "summary_path": str(summary_path),
            "fallback_count": 10**9,
            "objective_score": -1.0,
            "error": "missing summary",
        }

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "profile": profile,
        "status": "OK" if proc.returncode == 0 else "ERROR",
        "returncode": proc.returncode,
        "summary_path": str(summary_path),
        "fallback_count": int(summary.get("fallback_count", 10**9)),
        "fallback_rate": float(summary.get("fallback_rate", 1.0)),
        "objective_score": float(summary.get("objective_score", -1.0)),
        "expected_match_rate": float(summary.get("expected_match_rate", 0.0)),
        "reproducible_rate": float(summary.get("reproducible_rate", 0.0)),
        "term_micro_f1": summary.get("term_summary", {}).get("micro_f1"),
        "opcode_micro_f1": summary.get("opcode_summary", {}).get("micro_f1"),
        "fallback_reason_histogram": summary.get("fallback_reason_histogram", {}),
    }


def main(argv: List[str]) -> int:
    cases, out, model, profiles, seed, expand_factor, allow_fallback, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1

    out.mkdir(parents=True, exist_ok=True)
    log(
        "OK",
        f"phase=boot out={out} cases={cases} profiles={','.join(profiles)} model={model} expand_factor={expand_factor}",
    )

    results: List[Dict[str, object]] = []
    for profile in profiles:
        log("OK", f"phase=profile start profile={profile}")
        row = _run_profile(
            profile=profile,
            cases=cases,
            out_dir=out,
            model=model,
            seed=seed,
            expand_factor=expand_factor,
            allow_fallback=allow_fallback,
        )
        results.append(row)
        log(
            "OK",
            f"phase=profile end profile={profile} fallback_count={row.get('fallback_count')} objective={row.get('objective_score')}",
        )

    ranked = sorted(
        results,
        key=lambda x: (
            int(x.get("fallback_count", 10**9)),
            -float(x.get("objective_score", -1.0)),
            -float(x.get("expected_match_rate", 0.0)),
            -float(x.get("reproducible_rate", 0.0)),
        ),
    )

    best = ranked[0] if ranked else None
    report = {
        "schema": "IL_COMPILE_PROMPT_LOOP_v1",
        "cases": str(cases),
        "model": model,
        "seed": seed,
        "expand_factor": expand_factor,
        "allow_fallback": allow_fallback,
        "profiles": profiles,
        "results": results,
        "best": best,
    }

    report_path = out / "il.compile.prompt_loop.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if best is None:
        log("ERROR", "prompt_loop_summary status=ERROR reason=no_results")
        return 1

    log(
        "OK",
        f"prompt_loop_summary status=OK best_profile={best.get('profile')} fallback_count={best.get('fallback_count')} objective={best.get('objective_score')}",
    )
    return 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_compile_prompt_loop unexpected exception: {exc}")
        rc = 1
    if rc == 0:
        print("OK: il_compile_prompt_loop exit=0")
    else:
        print("ERROR: il_compile_prompt_loop exit=1")
