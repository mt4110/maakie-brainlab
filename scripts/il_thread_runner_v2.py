"""
S23-04: Compile -> Entry thread runner v2.

Stopless policy:
- no sys.exit
- continue per-case even if one case fails
- emit grep-friendly OK:/ERROR:/SKIP: logs
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.il_entry import run_il_entry
from src.il_compile import (
    DEFAULT_MODEL,
    DEFAULT_PROMPT_PROFILE,
    DEFAULT_PROVIDER,
    compile_request_bundle,
    normalize_prompt_profile,
)

CASE_SCHEMA = "IL_THREAD_RUNNER_V2_CASE_v1"
SUMMARY_SCHEMA = "IL_THREAD_RUNNER_V2_SUMMARY_v1"


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return (
        "python3 scripts/il_thread_runner_v2.py "
        "--cases <cases.jsonl> --mode <validate-only|run> --out <out_dir> "
        "[--provider <rule_based|local_llm>] [--model <name>] "
        "[--prompt-profile <v1|strict_json_v2|contract_json_v3>] [--seed <int>] [--no-fallback]"
    )


def _resolve_path(path_text: str) -> Path:
    p = Path(path_text).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def _safe_slug(raw: str) -> str:
    safe_chars = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-", "."}:
            safe_chars.append(ch)
        else:
            safe_chars.append("_")
    text = "".join(safe_chars).strip("._")
    return text or "case"


def _make_error(code: str, message: str, path: str = "") -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message, "retriable": False}
    if path:
        err["path"] = path
    return err


def parse_args(
    args: List[str],
) -> Tuple[Optional[Path], str, Optional[Path], str, str, str, int, bool, List[str], bool]:
    cases_path: Optional[Path] = None
    mode = "validate-only"
    out_dir: Optional[Path] = None
    provider = DEFAULT_PROVIDER
    model = DEFAULT_MODEL
    prompt_profile = DEFAULT_PROMPT_PROFILE
    seed = 7
    allow_fallback = True
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return (
            cases_path,
            mode,
            out_dir,
            provider,
            model,
            prompt_profile,
            seed,
            allow_fallback,
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
            cases_path = _resolve_path(args[i + 1])
            i += 2
        elif token == "--mode":
            if i + 1 >= len(args):
                errors.append("missing value for --mode")
                i += 1
                continue
            mode = args[i + 1].strip()
            i += 2
        elif token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out_dir = _resolve_path(args[i + 1])
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
        elif token == "--no-fallback":
            allow_fallback = False
            i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    if cases_path is None:
        errors.append("missing required --cases")
    if out_dir is None:
        errors.append("missing required --out")
    if mode not in {"validate-only", "run"}:
        errors.append(f"invalid --mode: {mode}")

    return (
        cases_path,
        mode,
        out_dir,
        provider,
        model,
        normalize_prompt_profile(prompt_profile),
        seed,
        allow_fallback,
        errors,
        False,
    )


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cases(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            raw = line.strip()
            if not raw:
                continue

            case: Dict[str, Any] = {
                "line": lineno,
                "id": f"line_{lineno:04d}",
                "request": {},
                "fixture_db": None,
                "errors": [],
            }
            try:
                obj = json.loads(raw)
            except Exception as exc:
                case["errors"].append(_make_error("E_CASE_SCHEMA", f"invalid json line: {exc}", path=f"/line/{lineno}"))
                rows.append(case)
                continue

            if not isinstance(obj, dict):
                case["errors"].append(_make_error("E_CASE_SCHEMA", "case row must be object", path=f"/line/{lineno}"))
                rows.append(case)
                continue

            case_id = obj.get("id")
            if isinstance(case_id, str) and case_id.strip():
                case["id"] = case_id.strip()
            else:
                case["errors"].append(_make_error("E_CASE_SCHEMA", "id must be non-empty string", path="/id"))

            request = obj.get("request")
            if isinstance(request, dict):
                case["request"] = request
            else:
                case["errors"].append(_make_error("E_CASE_SCHEMA", "request must be object", path="/request"))

            fixture_db = obj.get("fixture_db")
            if fixture_db is None:
                case["fixture_db"] = None
            elif isinstance(fixture_db, str) and fixture_db.strip():
                case["fixture_db"] = str(_resolve_path(fixture_db.strip()))
            else:
                case["errors"].append(
                    _make_error("E_CASE_SCHEMA", "fixture_db must be non-empty string when provided", path="/fixture_db")
                )

            rows.append(case)
    return rows


def _emit_compile_artifacts(case_compile_dir: Path, bundle: Dict[str, Any]) -> None:
    _write_json(case_compile_dir / "il.compile.request.normalized.json", bundle.get("normalized_request", {}))
    _write_text(case_compile_dir / "il.compile.prompt.txt", bundle.get("prompt_text", ""))
    _write_text(case_compile_dir / "il.compile.raw_response.txt", bundle.get("raw_response_text", ""))
    _write_json(case_compile_dir / "il.compile.report.json", bundle.get("report", {}))

    if bundle.get("status") == "OK" and bundle.get("compiled_output") is not None:
        _write_json(case_compile_dir / "il.compiled.json", bundle["compiled_output"])
        canonical = bundle.get("canonical_bytes") or b""
        with open(case_compile_dir / "il.compiled.canonical.json", "wb") as f:
            f.write(canonical)
    else:
        _write_json(case_compile_dir / "il.compile.error.json", {"errors": bundle.get("errors", [])})


def _bundle_from_case_errors(
    errors: List[Dict[str, Any]],
    provider: str,
    model: str,
    prompt_profile: str,
    seed: int,
) -> Dict[str, Any]:
    return {
        "status": "ERROR",
        "normalized_request": {},
        "prompt_text": "SYSTEM: case schema error before compile\n",
        "raw_response_text": "CASE_SCHEMA: no compile output",
        "compiled_output": None,
        "canonical_bytes": None,
        "errors": errors,
        "report": {
            "schema": "IL_COMPILE_REPORT_v1",
            "status": "ERROR",
            "error_count": len(errors),
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": seed, "stream": False},
            "prompt_template_id": "il_compile_prompt_v1",
            "prompt_profile": prompt_profile,
            "model": model,
            "provider_requested": provider,
            "provider_selected": provider,
            "fallback_used": False,
        },
    }


def run_thread_runner(
    cases_path: Path,
    mode: str,
    out_dir: Path,
    provider: str = DEFAULT_PROVIDER,
    model: str = DEFAULT_MODEL,
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    seed: int = 7,
    allow_fallback: bool = True,
) -> int:
    log(
        "OK",
        (
            f"phase=boot mode={mode} out={out_dir} cases={cases_path} provider={provider} "
            f"model={model} prompt_profile={prompt_profile} seed={seed} allow_fallback={allow_fallback}"
        ),
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cases_path.exists():
        log("ERROR", f"phase=input reason=file_not_found path={cases_path}")
        return 1

    try:
        cases = load_cases(cases_path)
    except Exception as exc:
        log("ERROR", f"phase=input reason=load_cases_failed err={exc}")
        return 1

    seen_ids: Dict[str, int] = {}
    records: List[Dict[str, Any]] = []
    stop = 0

    for idx, case in enumerate(cases, 1):
        case_id = str(case.get("id", f"line_{idx:04d}"))
        seen_ids[case_id] = seen_ids.get(case_id, 0) + 1
        case_errors = list(case.get("errors", []))
        if seen_ids[case_id] > 1:
            case_errors.append(_make_error("E_CASE_SCHEMA", f"duplicate case id: {case_id}", path="/id"))

        case_slug = _safe_slug(case_id)
        case_dir = out_dir / "cases" / f"{idx:04d}_{case_slug}"
        compile_dir = case_dir / "compile"
        entry_dir = case_dir / "entry"
        compile_dir.mkdir(parents=True, exist_ok=True)

        log("OK", f"phase=case_start index={idx} id={case_id}")
        if case_errors:
            case_errors.sort(key=lambda x: (x.get("path", ""), x.get("code", ""), x.get("message", "")))
            bundle = _bundle_from_case_errors(case_errors, provider, model, prompt_profile, seed)
        else:
            bundle = compile_request_bundle(
                case.get("request", {}),
                model=model,
                seed_override=seed,
                provider=provider,
                allow_fallback=allow_fallback,
                prompt_profile=prompt_profile,
            )

        _emit_compile_artifacts(compile_dir, bundle)

        compile_status = str(bundle.get("status", "ERROR"))
        compile_errors = bundle.get("errors", [])
        compile_error_codes = sorted(
            {
                str(err.get("code"))
                for err in compile_errors
                if isinstance(err, dict) and isinstance(err.get("code"), str) and err.get("code")
            }
        )

        entry_status = "SKIP"
        entry_stop = 0
        entry_skip_reason = ""
        if mode == "validate-only":
            entry_skip_reason = "mode_validate_only"
            log("SKIP", f"phase=entry index={idx} id={case_id} reason={entry_skip_reason}")
        elif compile_status != "OK":
            entry_skip_reason = "compile_failed_fail_closed"
            log("SKIP", f"phase=entry index={idx} id={case_id} reason={entry_skip_reason}")
        else:
            compiled_path = compile_dir / "il.compiled.json"
            if not compiled_path.exists():
                entry_status = "ERROR"
                entry_stop = 1
                stop = 1
                log("ERROR", f"phase=entry index={idx} id={case_id} reason=missing_compiled_json")
            else:
                try:
                    fixture_db = case.get("fixture_db")
                    entry_stop = int(run_il_entry(str(compiled_path), fixture_db_path=fixture_db, out_dir=str(entry_dir)))
                    if entry_stop == 0:
                        entry_status = "OK"
                        log("OK", f"phase=entry index={idx} id={case_id} status=OK")
                    else:
                        entry_status = "ERROR"
                        stop = 1
                        log("ERROR", f"phase=entry index={idx} id={case_id} status=ERROR")
                except Exception as exc:
                    entry_status = "ERROR"
                    entry_stop = 1
                    stop = 1
                    log("ERROR", f"phase=entry index={idx} id={case_id} reason=exception err={exc}")

        if compile_status != "OK":
            stop = 1

        artifacts: Dict[str, str] = {
            "compile_dir": str(compile_dir.relative_to(out_dir)),
            "compile_report": str((compile_dir / "il.compile.report.json").relative_to(out_dir)),
            "compile_error": str((compile_dir / "il.compile.error.json").relative_to(out_dir)),
            "compiled_json": str((compile_dir / "il.compiled.json").relative_to(out_dir)),
            "entry_dir": str(entry_dir.relative_to(out_dir)),
        }
        if not (compile_dir / "il.compile.error.json").exists():
            artifacts["compile_error"] = ""
        if not (compile_dir / "il.compiled.json").exists():
            artifacts["compiled_json"] = ""
        if not entry_dir.exists():
            artifacts["entry_dir"] = ""

        record = {
            "schema": CASE_SCHEMA,
            "index": idx,
            "id": case_id,
            "mode": mode,
            "compile_status": compile_status,
            "entry_status": entry_status,
            "entry_stop": entry_stop,
            "entry_skip_reason": entry_skip_reason,
            "compile_error_codes": compile_error_codes,
            "compile_error_count": len(compile_errors),
            "artifacts": artifacts,
        }
        records.append(record)
        log(
            "OK",
            (
                f"phase=case_end index={idx} id={case_id} compile={compile_status} "
                f"entry={entry_status} compile_errors={len(compile_errors)}"
            ),
        )

    cases_path_out = out_dir / "cases.jsonl"
    with open(cases_path_out, "w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    compile_ok_count = sum(1 for r in records if r["compile_status"] == "OK")
    compile_error_count = sum(1 for r in records if r["compile_status"] == "ERROR")
    entry_ok_count = sum(1 for r in records if r["entry_status"] == "OK")
    entry_error_count = sum(1 for r in records if r["entry_status"] == "ERROR")
    entry_skip_count = sum(1 for r in records if r["entry_status"] == "SKIP")

    summary = {
        "schema": SUMMARY_SCHEMA,
        "mode": mode,
        "provider": provider,
        "model": model,
        "prompt_profile": prompt_profile,
        "seed": seed,
        "allow_fallback": allow_fallback,
        "total_cases": len(records),
        "compile_ok_count": compile_ok_count,
        "compile_error_count": compile_error_count,
        "entry_ok_count": entry_ok_count,
        "entry_error_count": entry_error_count,
        "entry_skip_count": entry_skip_count,
        "error_count": compile_error_count + entry_error_count,
        "sha256_cases_jsonl": _sha256_file(cases_path_out),
    }
    _write_json(out_dir / "summary.json", summary)

    if summary["error_count"] > 0:
        stop = 1
    log(
        "OK",
        (
            f"phase=end STOP={stop} total={summary['total_cases']} compile_ok={compile_ok_count} "
            f"compile_error={compile_error_count} entry_ok={entry_ok_count} "
            f"entry_error={entry_error_count} entry_skip={entry_skip_count}"
        ),
    )
    return stop


def main(argv: List[str]) -> int:
    cases_path, mode, out_dir, provider, model, prompt_profile, seed, allow_fallback, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    assert cases_path is not None
    assert out_dir is not None
    return run_thread_runner(
        cases_path=cases_path,
        mode=mode,
        out_dir=out_dir,
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed=seed,
        allow_fallback=allow_fallback,
    )


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_thread_runner_v2 unexpected exception: {exc}")
        rc = 1
    if rc == 0:
        print("OK: il_thread_runner_v2 exit=0")
    else:
        print("ERROR: il_thread_runner_v2 exit=1")
