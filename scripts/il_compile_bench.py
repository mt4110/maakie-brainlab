"""
S23-03: compile quality bench (fixed input set, deterministic).

Metrics:
- expected_match_rate
- il_validity_rate (expected OK cases)
- reproducibility_rate
"""

import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.il_compile import DEFAULT_MODEL, DEFAULT_PROVIDER, compile_request_bundle


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return (
        "python3 scripts/il_compile_bench.py "
        "[--cases <jsonl>] [--out <dir>] [--provider <rule_based|local_llm>] "
        "[--model <name>] [--seed <int>] [--no-fallback]"
    )


def parse_args(args: List[str]) -> Tuple[Path, Path, str, str, int, bool, List[str], bool]:
    default_cases = repo_root / "tests" / "fixtures" / "il_compile" / "bench_cases.jsonl"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_out = repo_root / ".local" / "obs" / f"il_compile_bench_{ts}"
    cases_path = default_cases
    out_dir = default_out
    provider = DEFAULT_PROVIDER
    model = DEFAULT_MODEL
    seed = 7
    allow_fallback = True
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return cases_path, out_dir, provider, model, seed, allow_fallback, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--cases":
            if i + 1 >= len(args):
                errors.append("missing value for --cases")
                i += 1
                continue
            cases_path = Path(args[i + 1]).expanduser()
            if not cases_path.is_absolute():
                cases_path = (repo_root / cases_path).resolve()
            i += 2
        elif token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out_dir = Path(args[i + 1]).expanduser()
            if not out_dir.is_absolute():
                out_dir = (repo_root / out_dir).resolve()
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
        elif token == "--no-fallback":
            allow_fallback = False
            i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    return cases_path, out_dir, provider, model, seed, allow_fallback, errors, False


def load_cases(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError(f"line {lineno}: row must be object")
            case_id = obj.get("id")
            request = obj.get("request")
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"line {lineno}: id must be non-empty string")
            if not isinstance(request, dict):
                raise ValueError(f"line {lineno}: request must be object")
            expected_status = obj.get("expected_status", "OK")
            if expected_status not in {"OK", "ERROR"}:
                raise ValueError(f"line {lineno}: expected_status must be OK|ERROR")
            rows.append({"id": case_id, "request": request, "expected_status": expected_status})
    return rows


def _error_signature(errors: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    sig: List[Tuple[str, str, str]] = []
    for e in errors:
        sig.append((str(e.get("code", "")), str(e.get("path", "")), str(e.get("message", ""))))
    return sorted(sig)


def run_case(
    case: Dict[str, Any],
    provider: str,
    model: str,
    seed: int,
    allow_fallback: bool,
) -> Dict[str, Any]:
    first = compile_request_bundle(
        case["request"],
        provider=provider,
        model=model,
        seed_override=seed,
        allow_fallback=allow_fallback,
    )
    second = compile_request_bundle(
        case["request"],
        provider=provider,
        model=model,
        seed_override=seed,
        allow_fallback=allow_fallback,
    )

    status = first.get("status", "ERROR")
    status2 = second.get("status", "ERROR")
    expected = case["expected_status"]
    expected_match = status == expected

    if status == "OK" and status2 == "OK":
        reproducible = first.get("canonical_bytes") == second.get("canonical_bytes")
    elif status == "ERROR" and status2 == "ERROR":
        reproducible = _error_signature(first.get("errors", [])) == _error_signature(second.get("errors", []))
    else:
        reproducible = False

    report = first.get("report", {})
    result = {
        "id": case["id"],
        "expected_status": expected,
        "status": status,
        "expected_match": expected_match,
        "reproducible": reproducible,
        "error_count": len(first.get("errors", [])),
        "provider_requested": report.get("provider_requested", provider),
        "provider_selected": report.get("provider_selected", provider),
        "fallback_used": bool(report.get("fallback_used", False)),
    }
    if status == "OK":
        result["canonical_sha256"] = report.get("canonical_sha256", "")
    else:
        result["errors"] = first.get("errors", [])
    return result


def run_bench(
    cases_path: Path,
    out_dir: Path,
    provider: str,
    model: str,
    seed: int,
    allow_fallback: bool,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    log("OK", f"phase=boot cases={cases_path} out={out_dir}")

    if not cases_path.exists():
        log("ERROR", f"phase=input reason=file_not_found cases={cases_path}")
        return 1

    try:
        cases = load_cases(cases_path)
    except Exception as exc:
        log("ERROR", f"phase=input reason=load_failed detail={exc}")
        return 1

    rows: List[Dict[str, Any]] = []
    expected_ok_total = 0
    expected_ok_valid = 0
    expected_match_count = 0
    reproducible_count = 0
    fallback_count = 0

    for case in cases:
        log("OK", f"phase=case start id={case['id']}")
        row = run_case(
            case=case,
            provider=provider,
            model=model,
            seed=seed,
            allow_fallback=allow_fallback,
        )
        rows.append(row)
        if row["expected_status"] == "OK":
            expected_ok_total += 1
            if row["status"] == "OK":
                expected_ok_valid += 1
        if row["expected_match"]:
            expected_match_count += 1
        if row["reproducible"]:
            reproducible_count += 1
        if row["fallback_used"]:
            fallback_count += 1
        log(
            "OK",
            f"phase=case end id={case['id']} status={row['status']} expected={row['expected_status']} reproducible={row['reproducible']}",
        )

    total = len(rows)
    summary = {
        "schema": "IL_COMPILE_BENCH_SUMMARY_v1",
        "total_cases": total,
        "provider": provider,
        "model": model,
        "seed": seed,
        "allow_fallback": allow_fallback,
        "expected_match_count": expected_match_count,
        "expected_match_rate": (expected_match_count / total) if total > 0 else 0.0,
        "il_valid_cases": expected_ok_valid,
        "il_valid_total": expected_ok_total,
        "il_validity_rate": (expected_ok_valid / expected_ok_total) if expected_ok_total > 0 else 0.0,
        "reproducible_count": reproducible_count,
        "reproducible_rate": (reproducible_count / total) if total > 0 else 0.0,
        "fallback_count": fallback_count,
    }

    results_path = out_dir / "il.compile.bench.results.jsonl"
    summary_path = out_dir / "il.compile.bench.summary.json"
    with open(results_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, allow_nan=False)

    status = "OK" if summary["expected_match_rate"] == 1.0 and summary["reproducible_rate"] == 1.0 else "ERROR"
    if status == "OK":
        log("OK", f"bench_summary status=OK total={total} expected_match_rate={summary['expected_match_rate']:.3f} il_validity_rate={summary['il_validity_rate']:.3f} reproducible_rate={summary['reproducible_rate']:.3f}")
        return 0
    log("ERROR", f"bench_summary status=ERROR total={total} expected_match_rate={summary['expected_match_rate']:.3f} il_validity_rate={summary['il_validity_rate']:.3f} reproducible_rate={summary['reproducible_rate']:.3f}")
    return 1


def main(argv: List[str]) -> int:
    cases_path, out_dir, provider, model, seed, allow_fallback, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_bench(
        cases_path=cases_path,
        out_dir=out_dir,
        provider=provider,
        model=model,
        seed=seed,
        allow_fallback=allow_fallback,
    )


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_compile_bench unexpected exception: {exc}")
        rc = 1
    if rc == 0:
        print("OK: il_compile_bench exit=0")
    else:
        print("ERROR: il_compile_bench exit=1")
