"""
S23-03: compile quality bench (fixed input set + optional auto expansion).

Metrics:
- expected_match_rate
- il_validity_rate
- reproducibility_rate
- term/opcode precision, recall, F1 (micro + macro)
- fallback_rate
"""

import copy
import datetime
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.il_compile import (
    DEFAULT_MODEL,
    DEFAULT_PROMPT_PROFILE,
    DEFAULT_PROVIDER,
    compile_request_bundle,
)


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return (
        "python3 scripts/il_compile_bench.py "
        "[--cases <jsonl>] [--out <dir>] [--provider <rule_based|local_llm>] "
        "[--model <name>] [--prompt-profile <v1|strict_json_v2|contract_json_v3>] "
        "[--seed <int>] [--no-fallback] [--expand-factor <int>]"
    )


def parse_args(
    args: List[str],
) -> Tuple[Path, Path, str, str, str, int, bool, int, List[str], bool]:
    default_cases = repo_root / "tests" / "fixtures" / "il_compile" / "bench_cases.jsonl"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_out = repo_root / ".local" / "obs" / f"il_compile_bench_{ts}"
    cases_path = default_cases
    out_dir = default_out
    provider = DEFAULT_PROVIDER
    model = DEFAULT_MODEL
    prompt_profile = DEFAULT_PROMPT_PROFILE
    seed = 7
    allow_fallback = True
    expand_factor = 0
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return (
            cases_path,
            out_dir,
            provider,
            model,
            prompt_profile,
            seed,
            allow_fallback,
            expand_factor,
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
        elif token == "--expand-factor":
            if i + 1 >= len(args):
                errors.append("missing value for --expand-factor")
                i += 1
                continue
            raw = args[i + 1]
            try:
                expand_factor = int(raw)
                if expand_factor < 0:
                    errors.append("expand-factor must be >= 0")
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

    return (
        cases_path,
        out_dir,
        provider,
        model,
        prompt_profile,
        seed,
        allow_fallback,
        expand_factor,
        errors,
        False,
    )


def _normalize_terms(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: Set[str] = set()
    for v in values:
        if isinstance(v, str) and v.strip():
            out.add(v.strip().lower())
    return sorted(out)


def _normalize_opcodes(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: Set[str] = set()
    for v in values:
        if isinstance(v, str) and v.strip():
            out.add(v.strip().upper())
    return sorted(out)


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
            rows.append(
                {
                    "id": case_id,
                    "request": request,
                    "expected_status": expected_status,
                    "required_terms": _normalize_terms(obj.get("required_terms")),
                    "required_opcodes": _normalize_opcodes(obj.get("required_opcodes")),
                }
            )
    return rows


def expand_cases(cases: List[Dict[str, Any]], expand_factor: int, seed: int) -> List[Dict[str, Any]]:
    if expand_factor <= 0:
        return cases

    rng = random.Random(seed)
    expanded: List[Dict[str, Any]] = []
    templates = [
        lambda text: f"Please {text}",
        lambda text: f"{text}. Return deterministic plan.",
        lambda text: f"Need IL compile task: {text}",
        lambda text: f"compile request => {text}",
    ]

    for idx, case in enumerate(cases):
        expanded.append(case)
        if case["expected_status"] != "OK":
            continue

        base_text = str(case["request"].get("request_text", "")).strip()
        if not base_text:
            continue

        for n in range(expand_factor):
            new_case = copy.deepcopy(case)
            tmpl = templates[(idx + n + seed) % len(templates)]
            new_case["id"] = f"{case['id']}__aug{n+1:02d}"
            new_case["request"]["request_text"] = tmpl(base_text)

            ctx = new_case["request"].get("context")
            if isinstance(ctx, dict) and isinstance(ctx.get("keywords"), list):
                kws = [k for k in ctx.get("keywords", []) if isinstance(k, str)]
                rng.shuffle(kws)
                ctx["keywords"] = kws

            new_case["generated_from"] = case["id"]
            expanded.append(new_case)

    return expanded


def _error_signature(errors: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    sig: List[Tuple[str, str, str]] = []
    for e in errors:
        sig.append((str(e.get("code", "")), str(e.get("path", "")), str(e.get("message", ""))))
    return sorted(sig)


def _extract_predicted_terms(compiled_output: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(compiled_output, dict):
        return []
    il = compiled_output.get("il")
    if not isinstance(il, dict):
        return []
    return _normalize_terms(il.get("search_terms", []))


def _extract_predicted_opcodes(compiled_output: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(compiled_output, dict):
        return []
    il = compiled_output.get("il")
    if not isinstance(il, dict):
        return []
    opcodes = il.get("opcodes", [])
    out: Set[str] = set()
    if isinstance(opcodes, list):
        for item in opcodes:
            if isinstance(item, dict):
                op = item.get("op")
                if isinstance(op, str) and op.strip():
                    out.add(op.strip().upper())
    return sorted(out)


def _set_metrics(gold_items: List[str], pred_items: List[str], metric_name: str) -> Dict[str, Any]:
    gold = set(gold_items)
    pred = set(pred_items)
    evaluated = len(gold) > 0

    if not evaluated:
        return {
            "evaluated": False,
            "metric": metric_name,
            "gold": sorted(gold),
            "pred": sorted(pred),
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "precision": None,
            "recall": None,
            "f1": None,
            "exact": None,
        }

    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall > 0:
        f1 = 2.0 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "evaluated": True,
        "metric": metric_name,
        "gold": sorted(gold),
        "pred": sorted(pred),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact": sorted(gold) == sorted(pred),
    }


def run_case(
    case: Dict[str, Any],
    provider: str,
    model: str,
    prompt_profile: str,
    seed: int,
    allow_fallback: bool,
) -> Dict[str, Any]:
    first = compile_request_bundle(
        case["request"],
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed_override=seed,
        allow_fallback=allow_fallback,
    )
    second = compile_request_bundle(
        case["request"],
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
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
    compiled = first.get("compiled_output") if status == "OK" else None
    pred_terms = _extract_predicted_terms(compiled)
    pred_opcodes = _extract_predicted_opcodes(compiled)

    term_metrics = _set_metrics(case.get("required_terms", []), pred_terms, "terms")
    opcode_metrics = _set_metrics(case.get("required_opcodes", []), pred_opcodes, "opcodes")

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
        "fallback_reason": report.get("fallback_reason", ""),
        "term_metrics": term_metrics,
        "opcode_metrics": opcode_metrics,
    }
    if "generated_from" in case:
        result["generated_from"] = case["generated_from"]
    if status == "OK":
        result["canonical_sha256"] = report.get("canonical_sha256", "")
    else:
        result["errors"] = first.get("errors", [])
    return result


def _aggregate_metric(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    metrics = [r[key] for r in rows if isinstance(r.get(key), dict)]
    evaluated = [m for m in metrics if m.get("evaluated")]

    if not evaluated:
        return {
            "evaluated_cases": 0,
            "macro_precision": None,
            "macro_recall": None,
            "macro_f1": None,
            "micro_precision": None,
            "micro_recall": None,
            "micro_f1": None,
            "exact_match_rate": None,
        }

    macro_precision = sum(float(m["precision"]) for m in evaluated) / len(evaluated)
    macro_recall = sum(float(m["recall"]) for m in evaluated) / len(evaluated)
    macro_f1 = sum(float(m["f1"]) for m in evaluated) / len(evaluated)

    tp = sum(int(m["tp"]) for m in evaluated)
    fp = sum(int(m["fp"]) for m in evaluated)
    fn = sum(int(m["fn"]) for m in evaluated)
    micro_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    micro_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    micro_f1 = (
        2.0 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0
        else 0.0
    )
    exact_match_rate = (
        sum(1 for m in evaluated if bool(m.get("exact"))) / len(evaluated)
        if evaluated
        else None
    )

    return {
        "evaluated_cases": len(evaluated),
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        "exact_match_rate": exact_match_rate,
    }


def run_bench(
    cases_path: Path,
    out_dir: Path,
    provider: str,
    model: str,
    prompt_profile: str,
    seed: int,
    allow_fallback: bool,
    expand_factor: int,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    log(
        "OK",
        f"phase=boot cases={cases_path} out={out_dir} provider={provider} prompt_profile={prompt_profile} expand_factor={expand_factor}",
    )

    if not cases_path.exists():
        log("ERROR", f"phase=input reason=file_not_found cases={cases_path}")
        return 1

    try:
        base_cases = load_cases(cases_path)
    except Exception as exc:
        log("ERROR", f"phase=input reason=load_failed detail={exc}")
        return 1

    cases = expand_cases(base_cases, expand_factor=expand_factor, seed=seed)

    rows: List[Dict[str, Any]] = []
    expected_ok_total = 0
    expected_ok_valid = 0
    expected_match_count = 0
    reproducible_count = 0
    fallback_count = 0
    fallback_reason_histogram: Dict[str, int] = {}

    for case in cases:
        log("OK", f"phase=case start id={case['id']}")
        row = run_case(
            case=case,
            provider=provider,
            model=model,
            prompt_profile=prompt_profile,
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
            reason = str(row.get("fallback_reason", "")).strip() or "unknown"
            fallback_reason_histogram[reason] = fallback_reason_histogram.get(reason, 0) + 1
        log(
            "OK",
            f"phase=case end id={case['id']} status={row['status']} expected={row['expected_status']} reproducible={row['reproducible']}",
        )

    total = len(rows)
    fallback_rate = (fallback_count / total) if total > 0 else 0.0
    term_summary = _aggregate_metric(rows, "term_metrics")
    opcode_summary = _aggregate_metric(rows, "opcode_metrics")

    term_micro_f1 = float(term_summary["micro_f1"]) if term_summary["micro_f1"] is not None else 0.0
    opcode_micro_f1 = float(opcode_summary["micro_f1"]) if opcode_summary["micro_f1"] is not None else 0.0

    expected_match_rate = (expected_match_count / total) if total > 0 else 0.0
    reproducible_rate = (reproducible_count / total) if total > 0 else 0.0

    objective_score = (
        0.30 * expected_match_rate
        + 0.20 * reproducible_rate
        + 0.20 * (1.0 - fallback_rate)
        + 0.15 * term_micro_f1
        + 0.15 * opcode_micro_f1
    )

    summary = {
        "schema": "IL_COMPILE_BENCH_SUMMARY_v2",
        "total_cases": total,
        "base_cases": len(base_cases),
        "expanded_cases": total - len(base_cases),
        "provider": provider,
        "model": model,
        "prompt_profile": prompt_profile,
        "seed": seed,
        "allow_fallback": allow_fallback,
        "expand_factor": expand_factor,
        "expected_match_count": expected_match_count,
        "expected_match_rate": expected_match_rate,
        "il_valid_cases": expected_ok_valid,
        "il_valid_total": expected_ok_total,
        "il_validity_rate": (expected_ok_valid / expected_ok_total) if expected_ok_total > 0 else 0.0,
        "reproducible_count": reproducible_count,
        "reproducible_rate": reproducible_rate,
        "fallback_count": fallback_count,
        "fallback_rate": fallback_rate,
        "fallback_reason_histogram": dict(sorted(fallback_reason_histogram.items(), key=lambda kv: kv[0])),
        "term_summary": term_summary,
        "opcode_summary": opcode_summary,
        "objective_score": objective_score,
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
        log(
            "OK",
            "bench_summary status=OK "
            f"total={total} expected_match_rate={summary['expected_match_rate']:.3f} "
            f"il_validity_rate={summary['il_validity_rate']:.3f} reproducible_rate={summary['reproducible_rate']:.3f} "
            f"fallback_rate={summary['fallback_rate']:.3f} term_micro_f1={term_micro_f1:.3f} opcode_micro_f1={opcode_micro_f1:.3f} "
            f"objective_score={objective_score:.3f}",
        )
        return 0
    log(
        "ERROR",
        "bench_summary status=ERROR "
        f"total={total} expected_match_rate={summary['expected_match_rate']:.3f} "
        f"il_validity_rate={summary['il_validity_rate']:.3f} reproducible_rate={summary['reproducible_rate']:.3f} "
        f"fallback_rate={summary['fallback_rate']:.3f} term_micro_f1={term_micro_f1:.3f} opcode_micro_f1={opcode_micro_f1:.3f} "
        f"objective_score={objective_score:.3f}",
    )
    return 1


def main(argv: List[str]) -> int:
    (
        cases_path,
        out_dir,
        provider,
        model,
        prompt_profile,
        seed,
        allow_fallback,
        expand_factor,
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
    return run_bench(
        cases_path=cases_path,
        out_dir=out_dir,
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed=seed,
        allow_fallback=allow_fallback,
        expand_factor=expand_factor,
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
    sys.exit(rc)
