"""
S23-04: Compile -> Entry thread runner v2.

Stopless policy for core run logic:
- continue per-case even if one case fails
- emit grep-friendly OK:/ERROR:/SKIP: logs
- CLI wrapper returns the computed process status
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.il_compile import (
    DEFAULT_MODEL,
    DEFAULT_PROMPT_PROFILE,
    DEFAULT_PROVIDER,
    compile_request_bundle,
    normalize_prompt_profile,
    resolve_prompt_template_id,
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
        "[--prompt-profile <v1|strict_json_v2|contract_json_v3>] [--seed <int>] [--no-fallback] "
        "[--entry-timeout-sec <int>] [--entry-retries <int>] [--entry-script <path>]"
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
) -> Tuple[Optional[Path], str, Optional[Path], str, str, str, int, bool, int, int, Path, List[str], bool]:
    cases_path: Optional[Path] = None
    mode = "validate-only"
    out_dir: Optional[Path] = None
    provider = DEFAULT_PROVIDER
    model = DEFAULT_MODEL
    prompt_profile = DEFAULT_PROMPT_PROFILE
    seed = 7
    allow_fallback = True
    entry_timeout_sec = 30
    entry_retries = 0
    entry_script = repo_root / "scripts" / "il_entry.py"
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
            entry_timeout_sec,
            entry_retries,
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
        elif token == "--entry-retries":
            if i + 1 >= len(args):
                errors.append("missing value for --entry-retries")
                i += 1
                continue
            raw = args[i + 1]
            try:
                entry_retries = int(raw)
                if entry_retries < 0:
                    errors.append("entry-retries must be >= 0")
            except Exception:
                errors.append(f"invalid --entry-retries: {raw}")
            i += 2
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
        entry_timeout_sec,
        entry_retries,
        entry_script,
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


def _append_jsonl_line(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_summary(
    records: List[Dict[str, Any]],
    mode: str,
    provider: str,
    model: str,
    prompt_profile: str,
    seed: int,
    allow_fallback: bool,
    entry_timeout_sec: int,
    entry_retries: int,
    selected_entry_script: Path,
    cases_jsonl_sha256: str = "",
) -> Dict[str, Any]:
    compile_ok_count = sum(1 for r in records if r["compile_status"] == "OK")
    compile_error_count = sum(1 for r in records if r["compile_status"] == "ERROR")
    entry_ok_count = sum(1 for r in records if r["entry_status"] == "OK")
    entry_error_count = sum(1 for r in records if r["entry_status"] == "ERROR")
    entry_skip_count = sum(1 for r in records if r["entry_status"] == "SKIP")
    retries_used_count = sum(max(0, int(r.get("entry_attempts", 0)) - 1) for r in records)
    return {
        "schema": SUMMARY_SCHEMA,
        "mode": mode,
        "provider": provider,
        "model": model,
        "prompt_profile": prompt_profile,
        "seed": seed,
        "allow_fallback": allow_fallback,
        "entry_timeout_sec": entry_timeout_sec,
        "entry_retries": entry_retries,
        "entry_script": str(selected_entry_script),
        "total_cases": len(records),
        "compile_ok_count": compile_ok_count,
        "compile_error_count": compile_error_count,
        "entry_ok_count": entry_ok_count,
        "entry_error_count": entry_error_count,
        "entry_skip_count": entry_skip_count,
        "retries_used_count": retries_used_count,
        "error_count": compile_error_count + entry_error_count,
        "sha256_cases_jsonl": cases_jsonl_sha256,
    }


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
    prompt_template_id = resolve_prompt_template_id(prompt_profile)
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
            "prompt_template_id": prompt_template_id,
            "prompt_profile": prompt_profile,
            "model": model,
            "provider_requested": provider,
            "provider_selected": provider,
            "fallback_used": False,
        },
    }


def _run_entry_subprocess(
    entry_script: Path,
    compiled_path: Path,
    entry_dir: Path,
    fixture_db: Optional[str],
    entry_timeout_sec: int,
    attempt_index: int,
) -> Tuple[int, List[str], str]:
    entry_dir.mkdir(parents=True, exist_ok=True)
    cmd: List[str] = [
        "python3",
        str(entry_script),
        str(compiled_path),
        "--out",
        str(entry_dir),
    ]
    if fixture_db:
        cmd.extend(["--fixture-db", fixture_db])

    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=entry_timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        _write_text(entry_dir / f"entry.stdout.attempt{attempt_index:02d}.log", stdout)
        _write_text(entry_dir / f"entry.stderr.attempt{attempt_index:02d}.log", stderr)
        _write_text(entry_dir / "entry.stdout.log", stdout)
        _write_text(entry_dir / "entry.stderr.log", stderr)
        return 1, ["E_TIMEOUT"], f"entry_timeout_{entry_timeout_sec}s"
    except Exception as exc:
        _write_text(entry_dir / f"entry.stdout.attempt{attempt_index:02d}.log", "")
        _write_text(entry_dir / f"entry.stderr.attempt{attempt_index:02d}.log", str(exc))
        _write_text(entry_dir / "entry.stdout.log", "")
        _write_text(entry_dir / "entry.stderr.log", str(exc))
        return 1, ["E_ENTRY_SUBPROCESS"], f"entry_subprocess_exception:{exc}"

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    _write_text(entry_dir / f"entry.stdout.attempt{attempt_index:02d}.log", stdout)
    _write_text(entry_dir / f"entry.stderr.attempt{attempt_index:02d}.log", stderr)
    _write_text(entry_dir / "entry.stdout.log", stdout)
    _write_text(entry_dir / "entry.stderr.log", stderr)
    combined = stdout + stderr

    if proc.returncode != 0:
        return 1, ["E_ENTRY_RETURN_CODE"], f"entry_returncode_{proc.returncode}"
    if "OK: phase=end STOP=0" in combined:
        report_path = entry_dir / "il.exec.report.json"
        if report_path.exists():
            return 0, [], ""
        return 1, ["E_ENTRY_ARTIFACT_MISSING"], "entry_report_missing"
    if "OK: phase=end STOP=1" in combined:
        return 1, ["E_ENTRY_STOP"], "entry_reported_stop_1"
    return 1, ["E_ENTRY_PROTOCOL"], "entry_missing_stop_marker"


def run_thread_runner(
    cases_path: Path,
    mode: str,
    out_dir: Path,
    provider: str = DEFAULT_PROVIDER,
    model: str = DEFAULT_MODEL,
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    seed: int = 7,
    allow_fallback: bool = True,
    entry_timeout_sec: int = 30,
    entry_retries: int = 0,
    entry_script: Optional[Path] = None,
) -> int:
    selected_entry_script = entry_script or (repo_root / "scripts" / "il_entry.py")
    log(
        "OK",
        (
            f"phase=boot mode={mode} out={out_dir} cases={cases_path} provider={provider} "
            f"model={model} prompt_profile={prompt_profile} seed={seed} allow_fallback={allow_fallback} "
            f"entry_timeout_sec={entry_timeout_sec} entry_retries={entry_retries} entry_script={selected_entry_script}"
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
    cases_partial_path = out_dir / "cases.partial.jsonl"
    summary_partial_path = out_dir / "summary.partial.json"
    try:
        if cases_partial_path.exists():
            cases_partial_path.unlink()
    except Exception as exc:
        log("ERROR", f"phase=checkpoint reason=cannot_reset_cases_partial err={exc}")
        stop = 1
    try:
        if summary_partial_path.exists():
            summary_partial_path.unlink()
    except Exception as exc:
        log("ERROR", f"phase=checkpoint reason=cannot_reset_summary_partial err={exc}")
        stop = 1

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
        entry_error_codes: List[str] = []
        entry_error_reason = ""
        entry_attempts = 0
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
                entry_error_codes = ["E_MISSING_COMPILED"]
                entry_error_reason = "missing_compiled_json"
                entry_attempts = 1
                stop = 1
                log("ERROR", f"phase=entry index={idx} id={case_id} reason=missing_compiled_json")
            else:
                try:
                    fixture_db = case.get("fixture_db")
                    total_attempts = 1 + max(0, entry_retries)
                    for attempt in range(1, total_attempts + 1):
                        entry_attempts = attempt
                        entry_stop, entry_error_codes, entry_error_reason = _run_entry_subprocess(
                            entry_script=selected_entry_script,
                            compiled_path=compiled_path,
                            entry_dir=entry_dir,
                            fixture_db=fixture_db,
                            entry_timeout_sec=entry_timeout_sec,
                            attempt_index=attempt,
                        )
                        if entry_stop == 0:
                            entry_status = "OK"
                            log("OK", f"phase=entry index={idx} id={case_id} status=OK attempts={attempt}")
                            break

                        if attempt < total_attempts:
                            log(
                                "SKIP",
                                (
                                    f"phase=entry_retry index={idx} id={case_id} attempt={attempt} "
                                    f"reason={entry_error_reason} next_attempt={attempt+1}"
                                ),
                            )
                            continue

                        entry_status = "ERROR"
                        stop = 1
                        log(
                            "ERROR",
                            (
                                f"phase=entry index={idx} id={case_id} status=ERROR attempts={attempt} "
                                f"codes={','.join(entry_error_codes)} reason={entry_error_reason}"
                            ),
                        )
                except Exception as exc:
                    entry_status = "ERROR"
                    entry_stop = 1
                    entry_error_codes = ["E_ENTRY_EXCEPTION"]
                    entry_error_reason = str(exc)
                    entry_attempts = max(entry_attempts, 1)
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
            "entry_stdout": str((entry_dir / "entry.stdout.log").relative_to(out_dir)),
            "entry_stderr": str((entry_dir / "entry.stderr.log").relative_to(out_dir)),
        }
        if not (compile_dir / "il.compile.error.json").exists():
            artifacts["compile_error"] = ""
        if not (compile_dir / "il.compiled.json").exists():
            artifacts["compiled_json"] = ""
        if not entry_dir.exists():
            artifacts["entry_dir"] = ""
            artifacts["entry_stdout"] = ""
            artifacts["entry_stderr"] = ""
        if entry_dir.exists() and not (entry_dir / "entry.stdout.log").exists():
            artifacts["entry_stdout"] = ""
        if entry_dir.exists() and not (entry_dir / "entry.stderr.log").exists():
            artifacts["entry_stderr"] = ""

        record = {
            "schema": CASE_SCHEMA,
            "index": idx,
            "id": case_id,
            "mode": mode,
            "compile_status": compile_status,
            "entry_status": entry_status,
            "entry_stop": entry_stop,
            "entry_attempts": entry_attempts,
            "entry_skip_reason": entry_skip_reason,
            "entry_error_codes": entry_error_codes,
            "entry_error_reason": entry_error_reason,
            "compile_error_codes": compile_error_codes,
            "compile_error_count": len(compile_errors),
            "artifacts": artifacts,
        }
        records.append(record)
        try:
            _append_jsonl_line(cases_partial_path, record)
        except Exception as exc:
            log("ERROR", f"phase=checkpoint index={idx} id={case_id} reason=partial_case_write_failed err={exc}")
            stop = 1

        try:
            partial_summary = _build_summary(
                records=records,
                mode=mode,
                provider=provider,
                model=model,
                prompt_profile=prompt_profile,
                seed=seed,
                allow_fallback=allow_fallback,
                entry_timeout_sec=entry_timeout_sec,
                entry_retries=entry_retries,
                selected_entry_script=selected_entry_script,
                cases_jsonl_sha256="",
            )
            _write_json(summary_partial_path, partial_summary)
        except Exception as exc:
            log("ERROR", f"phase=checkpoint index={idx} id={case_id} reason=partial_summary_write_failed err={exc}")
            stop = 1

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

    summary = _build_summary(
        records=records,
        mode=mode,
        provider=provider,
        model=model,
        prompt_profile=prompt_profile,
        seed=seed,
        allow_fallback=allow_fallback,
        entry_timeout_sec=entry_timeout_sec,
        entry_retries=entry_retries,
        selected_entry_script=selected_entry_script,
        cases_jsonl_sha256=_sha256_file(cases_path_out),
    )
    _write_json(out_dir / "summary.json", summary)

    if summary["error_count"] > 0:
        stop = 1
    log(
        "OK",
        (
            f"phase=end STOP={stop} total={summary['total_cases']} compile_ok={summary['compile_ok_count']} "
            f"compile_error={summary['compile_error_count']} entry_ok={summary['entry_ok_count']} "
            f"entry_error={summary['entry_error_count']} entry_skip={summary['entry_skip_count']}"
        ),
    )
    return stop


def main(argv: List[str]) -> int:
    (
        cases_path,
        mode,
        out_dir,
        provider,
        model,
        prompt_profile,
        seed,
        allow_fallback,
        entry_timeout_sec,
        entry_retries,
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
        entry_timeout_sec=entry_timeout_sec,
        entry_retries=entry_retries,
        entry_script=entry_script,
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
    sys.exit(rc)
