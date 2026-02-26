"""
S23-09: artifact doctor for il_thread_runner_v2 outputs.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

repo_root = Path(__file__).resolve().parent.parent


def log(level: str, message: str) -> None:
    print(f"{level}: {message}")


def usage() -> str:
    return "python3 scripts/il_thread_runner_v2_doctor.py --run-dir <runner_out_dir>"


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


def parse_args(args: List[str]) -> Tuple[Path, List[str], bool]:
    run_dir = Path(".")
    errors: List[str] = []
    show_help = False

    if "--help" in args or "-h" in args:
        return run_dir, errors, True

    i = 0
    seen_run_dir = False
    while i < len(args):
        token = args[i]
        if token == "--run-dir":
            if i + 1 >= len(args):
                errors.append("missing value for --run-dir")
                i += 1
                continue
            run_dir = _resolve_path(args[i + 1])
            seen_run_dir = True
            i += 2
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1
    if not seen_run_dir:
        errors.append("missing required --run-dir")
    return run_dir, errors, show_help


def _load_cases(path: Path) -> List[Dict[str, Any]]:
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


def run_doctor(run_dir: Path) -> int:
    log("OK", f"phase=boot run_dir={run_dir}")
    summary_path = run_dir / "summary.json"
    cases_path = run_dir / "cases.jsonl"
    errors: List[str] = []

    if not summary_path.exists():
        errors.append(f"missing summary.json: {summary_path}")
    if not cases_path.exists():
        errors.append(f"missing cases.jsonl: {cases_path}")
    if errors:
        for e in errors:
            log("ERROR", e)
        log("ERROR", f"doctor_summary status=ERROR errors={len(errors)}")
        return 1

    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log("ERROR", f"summary parse failed: {exc}")
        return 1
    try:
        cases = _load_cases(cases_path)
    except Exception as exc:
        log("ERROR", f"cases parse failed: {exc}")
        return 1

    total_cases = int(summary.get("total_cases", -1))
    if total_cases != len(cases):
        errors.append(f"summary total_cases mismatch: summary={total_cases} cases={len(cases)}")

    sha_summary = str(summary.get("sha256_cases_jsonl", ""))
    sha_actual = _sha256_file(cases_path)
    if sha_summary != sha_actual:
        errors.append(f"sha256_cases_jsonl mismatch: summary={sha_summary} actual={sha_actual}")

    for idx, case in enumerate(cases, 1):
        case_id = str(case.get("id", f"idx{idx}"))
        artifacts = case.get("artifacts", {})
        if not isinstance(artifacts, dict):
            errors.append(f"case={case_id} artifacts must be object")
            continue

        compile_report_rel = str(artifacts.get("compile_report", ""))
        if not compile_report_rel:
            errors.append(f"case={case_id} missing artifacts.compile_report")
        else:
            if not (run_dir / compile_report_rel).exists():
                errors.append(f"case={case_id} compile report missing: {compile_report_rel}")

        compile_status = str(case.get("compile_status", ""))
        if compile_status == "OK":
            compiled_rel = str(artifacts.get("compiled_json", ""))
            if not compiled_rel or not (run_dir / compiled_rel).exists():
                errors.append(f"case={case_id} compiled_json missing for compile_status=OK")
        elif compile_status == "ERROR":
            compile_error_rel = str(artifacts.get("compile_error", ""))
            if not compile_error_rel or not (run_dir / compile_error_rel).exists():
                errors.append(f"case={case_id} compile_error missing for compile_status=ERROR")

        entry_status = str(case.get("entry_status", ""))
        if entry_status == "OK":
            entry_dir_rel = str(artifacts.get("entry_dir", ""))
            if not entry_dir_rel:
                errors.append(f"case={case_id} entry_dir missing for entry_status=OK")
            else:
                entry_report = run_dir / entry_dir_rel / "il.exec.report.json"
                if not entry_report.exists():
                    errors.append(f"case={case_id} il.exec.report.json missing for entry_status=OK")

    if errors:
        for e in errors:
            log("ERROR", e)
        log("ERROR", f"doctor_summary status=ERROR errors={len(errors)}")
        return 1
    log("OK", f"doctor_summary status=OK cases={len(cases)} sha256={sha_actual}")
    return 0


def main(argv: List[str]) -> int:
    run_dir, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_doctor(run_dir)


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_thread_runner_v2_doctor unexpected exception: {exc}")
        rc = 1
    if rc == 0:
        print("OK: il_thread_runner_v2_doctor exit=0")
    else:
        print("ERROR: il_thread_runner_v2_doctor exit=1")
