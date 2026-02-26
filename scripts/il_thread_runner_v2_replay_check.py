"""
S23-06: replay determinism check for il_thread_runner_v2.

Runs the same input twice and compares cases.jsonl sha256.
"""

import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import List, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.il_thread_runner_v2 import run_thread_runner


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return (
        "python3 scripts/il_thread_runner_v2_replay_check.py "
        "[--cases <jsonl>] [--out <dir>] [--mode <validate-only|run>] "
        "[--provider <rule_based|local_llm>] [--model <name>] "
        "[--prompt-profile <v1|strict_json_v2|contract_json_v3>] [--seed <int>] "
        "[--entry-timeout-sec <int>] [--entry-script <path>] [--no-fallback]"
    )


def _resolve_path(text: str) -> Path:
    p = Path(text).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args(args: List[str]) -> Tuple[Path, Path, str, str, str, str, int, bool, int, Path, List[str], bool]:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_cases = repo_root / "tests" / "fixtures" / "il_thread_runner" / "cases_smoke.jsonl"
    default_out = repo_root / ".local" / "obs" / f"il_thread_runner_v2_replay_{ts}"
    cases = default_cases
    out = default_out
    mode = "validate-only"
    provider = "rule_based"
    model = "rule_based_v1"
    prompt_profile = "v1"
    seed = 7
    allow_fallback = True
    entry_timeout_sec = 30
    entry_script = repo_root / "scripts" / "il_entry.py"
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return (
            cases,
            out,
            mode,
            provider,
            model,
            prompt_profile,
            seed,
            allow_fallback,
            entry_timeout_sec,
            entry_script,
            errors,
            True,
        )

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--cases":
            if i + 1 >= len(args):
                errors.append("missing value for --cases")
                i += 1
                continue
            cases = _resolve_path(args[i + 1])
            i += 2
        elif token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out = _resolve_path(args[i + 1])
            i += 2
        elif token == "--mode":
            if i + 1 >= len(args):
                errors.append("missing value for --mode")
                i += 1
                continue
            mode = args[i + 1].strip()
            i += 2
        elif token == "--provider":
            if i + 1 >= len(args):
                errors.append("missing value for --provider")
                i += 1
                continue
            provider = args[i + 1]
            i += 2
        elif token == "--model":
            if i + 1 >= len(args):
                errors.append("missing value for --model")
                i += 1
                continue
            model = args[i + 1]
            i += 2
        elif token == "--prompt-profile":
            if i + 1 >= len(args):
                errors.append("missing value for --prompt-profile")
                i += 1
                continue
            prompt_profile = args[i + 1]
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
        elif token == "--entry-timeout-sec":
            if i + 1 >= len(args):
                errors.append("missing value for --entry-timeout-sec")
                i += 1
                continue
            raw = args[i + 1]
            try:
                entry_timeout_sec = int(raw)
                if entry_timeout_sec <= 0:
                    errors.append("entry-timeout-sec must be > 0")
            except Exception:
                errors.append(f"invalid --entry-timeout-sec: {raw}")
            i += 2
        elif token == "--entry-script":
            if i + 1 >= len(args):
                errors.append("missing value for --entry-script")
                i += 1
                continue
            entry_script = _resolve_path(args[i + 1])
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

    if mode not in {"validate-only", "run"}:
        errors.append(f"invalid --mode: {mode}")
    return (
        cases,
        out,
        mode,
        provider,
        model,
        prompt_profile,
        seed,
        allow_fallback,
        entry_timeout_sec,
        entry_script,
        errors,
        False,
    )


def run_replay_check(
    cases: Path,
    out: Path,
    mode: str,
    provider: str,
    model: str,
    prompt_profile: str,
    seed: int,
    allow_fallback: bool,
    entry_timeout_sec: int,
    entry_script: Path,
) -> int:
    out.mkdir(parents=True, exist_ok=True)
    log("OK", f"phase=boot out={out} cases={cases} mode={mode}")

    run1 = out / "run1"
    run2 = out / "run2"
    stop1 = run_thread_runner(
        cases_path=cases,
        mode=mode,
        out_dir=run1,
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed=seed,
        allow_fallback=allow_fallback,
        entry_timeout_sec=entry_timeout_sec,
        entry_script=entry_script,
    )
    stop2 = run_thread_runner(
        cases_path=cases,
        mode=mode,
        out_dir=run2,
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed=seed,
        allow_fallback=allow_fallback,
        entry_timeout_sec=entry_timeout_sec,
        entry_script=entry_script,
    )

    run1_cases = run1 / "cases.jsonl"
    run2_cases = run2 / "cases.jsonl"
    run1_sha = _sha256_file(run1_cases) if run1_cases.exists() else ""
    run2_sha = _sha256_file(run2_cases) if run2_cases.exists() else ""
    match = bool(run1_sha and run2_sha and run1_sha == run2_sha)
    status = "OK" if match and stop1 == 0 and stop2 == 0 else "ERROR"

    report = {
        "schema": "IL_THREAD_REPLAY_CHECK_v1",
        "status": status,
        "mode": mode,
        "provider": provider,
        "model": model,
        "prompt_profile": prompt_profile,
        "seed": seed,
        "allow_fallback": allow_fallback,
        "entry_timeout_sec": entry_timeout_sec,
        "entry_script": str(entry_script),
        "run1_stop": stop1,
        "run2_stop": stop2,
        "run1_sha256_cases_jsonl": run1_sha,
        "run2_sha256_cases_jsonl": run2_sha,
        "match": match,
    }
    report_path = out / "il.thread.replay.report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if status == "OK":
        log("OK", f"replay_summary status=OK sha={run1_sha}")
        return 0
    log(
        "ERROR",
        (
            f"replay_summary status=ERROR stop1={stop1} stop2={stop2} "
            f"sha1={run1_sha} sha2={run2_sha} match={match}"
        ),
    )
    return 1


def main(argv: List[str]) -> int:
    (
        cases,
        out,
        mode,
        provider,
        model,
        prompt_profile,
        seed,
        allow_fallback,
        entry_timeout_sec,
        entry_script,
        errors,
        show_help,
    ) = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_replay_check(
        cases=cases,
        out=out,
        mode=mode,
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed=seed,
        allow_fallback=allow_fallback,
        entry_timeout_sec=entry_timeout_sec,
        entry_script=entry_script,
    )


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_thread_runner_v2_replay_check unexpected exception: {exc}")
        rc = 1
    if rc == 0:
        print("OK: il_thread_runner_v2_replay_check exit=0")
    else:
        print("ERROR: il_thread_runner_v2_replay_check exit=1")
    sys.exit(rc)
