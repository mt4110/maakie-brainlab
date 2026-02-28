#!/usr/bin/env python3
"""
S31-05: IL doctor entrypoint.

Runs lightweight health checks for IL workflow in stopless mode.
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.il_compile import compile_request_bundle


def usage() -> str:
    return "python3 scripts/il_doctor.py [--out <dir>]"


def _resolve_path(text: str) -> Path:
    p = Path(text).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def parse_args(args: List[str]) -> Tuple[Path, List[str], bool]:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = repo_root / ".local" / "obs" / f"il_doctor_{ts}"
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return out, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out = _resolve_path(args[i + 1])
            i += 2
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    return out, errors, False


def _run(cmd: List[str], cwd: Path) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except Exception as exc:
        return 1, str(exc)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def _default_compile_request(*, request_text: str, artifact: bool = True, max_steps: int = 4) -> Dict[str, object]:
    pointers = [{"path": "tests/fixtures/il_exec/retrieve_db.json"}] if artifact else []
    return {
        "schema": "IL_COMPILE_REQUEST_v1",
        "request_text": request_text,
        "context": {"keywords": ["alpha"]},
        "constraints": {
            "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
            "forbidden_keys": [],
            "max_steps": max_steps,
        },
        "artifact_pointers": pointers,
        "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
    }


def _run_compile_health_checks() -> Tuple[List[Dict[str, object]], List[str], List[str]]:
    checks: List[Dict[str, object]] = []
    fix_hints: List[str] = []
    next_commands: List[str] = []

    # 1) schema fail-closed check
    bad_req = _default_compile_request(request_text="", artifact=True)
    bundle_schema = compile_request_bundle(bad_req, provider="rule_based")
    schema_codes = [str(e.get("code", "")) for e in bundle_schema.get("errors", []) if isinstance(e, dict)]
    schema_ok = bundle_schema.get("status") == "ERROR" and "E_SCHEMA" in schema_codes
    checks.append({"name": "compile_schema_fail_closed", "status": "OK" if schema_ok else "ERROR"})
    if not schema_ok:
        fix_hints.append("compile schema guard drift: E_SCHEMA is not returned for invalid request_text.")
        next_commands.append("python3 -m unittest -v tests/test_il_compile.py tests/test_s32_compile_confidence_contract.py")

    # 2) auto profile selection report check
    profile_req = _default_compile_request(request_text="find alpha overview", artifact=True)
    bundle_profile = compile_request_bundle(profile_req, provider="rule_based", prompt_profile="auto")
    report_profile = bundle_profile.get("report", {})
    profile_ok = (
        bundle_profile.get("status") == "OK"
        and str(report_profile.get("profile_selected_by", "")) == "auto"
        and bool(report_profile.get("prompt_profile"))
    )
    checks.append({"name": "compile_profile_selection", "status": "OK" if profile_ok else "ERROR"})
    if not profile_ok:
        fix_hints.append("compile profile auto-selection report is missing profile_selected_by or prompt_profile.")
        next_commands.append("python3 -m unittest -v tests/test_s32_compile_profile_autoselect.py")

    # 3) parse repair guard check
    repair_raw = (
        '{"il":{"opcodes":[{"op":"SEARCH_TERMS","args":{}},{"op":"RETRIEVE","args":{}}],"search_terms":["alpha"]},'
        '"meta":{"version":"il_contract_v1","generator":"local"},'
        '"evidence":{"notes":"ok"},}'
    )

    def adapter(_prompt: str, _model: str, _det: dict) -> str:
        return repair_raw

    repair_req = _default_compile_request(request_text="find alpha", artifact=True)
    bundle_repair = compile_request_bundle(
        repair_req,
        provider="local_llm",
        allow_fallback=False,
        llm_adapter=adapter,
    )
    report_repair = bundle_repair.get("report", {})
    repair_ok = (
        bundle_repair.get("status") == "OK"
        and bool(report_repair.get("repair_applied"))
        and str(report_repair.get("repair_rule_id", "")) == "R_PARSE_TRAILING_COMMA"
    )
    checks.append({"name": "compile_parse_repair_guard", "status": "OK" if repair_ok else "ERROR"})
    if not repair_ok:
        fix_hints.append("parse repair guard did not apply expected bounded rule (R_PARSE_TRAILING_COMMA).")
        next_commands.append("python3 -m unittest -v tests/test_s32_compile_parse_repair_v3.py")

    # 4) confidence contract check
    confidence_req = _default_compile_request(request_text="alpha", artifact=False, max_steps=6)
    bundle_conf = compile_request_bundle(confidence_req, provider="rule_based")
    report_conf = bundle_conf.get("report", {})
    confidence_ok = (
        bundle_conf.get("status") == "OK"
        and isinstance(report_conf.get("confidence"), (int, float))
        and report_conf.get("confidence_status") in {"OK", "LOW"}
        and isinstance(report_conf.get("confidence_factors"), list)
    )
    checks.append({"name": "compile_confidence_contract", "status": "OK" if confidence_ok else "ERROR"})
    if not confidence_ok:
        fix_hints.append("compile confidence fields are missing in report (confidence/confidence_status/confidence_factors).")
        next_commands.append("python3 -m unittest -v tests/test_s32_compile_confidence_contract.py")

    return checks, fix_hints, next_commands


def run_doctor(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: List[Dict[str, object]] = []

    checks = [
        (
            "workspace_init",
            [
                "python3",
                str(repo_root / "scripts" / "il_workspace_init.py"),
                "--out",
                str(out_dir / "workspace"),
                "--force",
            ],
            ["OK: workspace_initialized"],
        ),
        (
            "lint_fixture",
            [
                "python3",
                str(repo_root / "scripts" / "il_lint.py"),
                "--il",
                str(repo_root / "tests" / "fixtures" / "il_exec" / "il_min.json"),
                "--out",
                str(out_dir / "lint.report.json"),
            ],
            ["OK: lint_status=OK"],
        ),
        (
            "compile_entry_smoke",
            ["python3", str(repo_root / "scripts" / "il_compile_entry_smoke.py")],
            ["OK: smoke_summary STOP=0"],
        ),
        (
            "thread_smoke",
            [
                "python3",
                str(repo_root / "scripts" / "il_thread_runner_v2_smoke.py"),
                "--out",
                str(out_dir / "thread_smoke"),
            ],
            ["OK: smoke_summary STOP=0"],
        ),
    ]

    hint_rules = {
        "workspace_init": {
            "hint": "workspace template generation failed; verify --out path permissions and template options.",
            "next_command": "python3 scripts/il_workspace_init.py --out .local/obs/il_ws --force",
        },
        "lint_fixture": {
            "hint": "fixture IL failed lint; inspect IL schema and opcode/args shape.",
            "next_command": "python3 scripts/il_lint.py --il tests/fixtures/il_exec/il_min.json --out .local/obs/il_lint.report.json",
        },
        "compile_entry_smoke": {
            "hint": "compile/entry smoke failed; inspect compile and entry artifacts for first failing phase.",
            "next_command": "python3 scripts/il_compile_entry_smoke.py",
        },
        "thread_smoke": {
            "hint": "thread smoke failed; inspect summary/failure digest and retry or lock conditions.",
            "next_command": "python3 scripts/il_thread_runner_v2_smoke.py --out .local/obs/il_thread_smoke",
        },
    }

    for name, cmd, expected in checks:
        rc, output = _run(cmd, repo_root)
        (out_dir / f"{name}.log").write_text(output, encoding="utf-8")
        ok = rc == 0 and all(mark in output for mark in expected)
        steps.append({"name": name, "rc": rc, "status": "OK" if ok else "ERROR"})
        if ok:
            print(f"OK: doctor_step={name} status=OK")
        else:
            print(f"ERROR: doctor_step={name} status=ERROR")

    compile_checks, compile_fix_hints, compile_next_commands = _run_compile_health_checks()
    compile_error_count = sum(1 for c in compile_checks if c.get("status") != "OK")
    compile_health = {
        "status": "OK" if compile_error_count == 0 else "WARN",
        "checks": compile_checks,
        "error_count": compile_error_count,
        "fix_hints": compile_fix_hints,
        "next_commands": compile_next_commands,
    }
    if compile_error_count == 0:
        print("OK: doctor_step=compile_health status=OK")
    else:
        print(f"ERROR: doctor_step=compile_health status=WARN errors={compile_error_count}")

    fix_hints: List[str] = []
    next_commands: List[str] = []
    for step in steps:
        if step.get("status") == "OK":
            continue
        rule = hint_rules.get(str(step.get("name", "")), {})
        hint = str(rule.get("hint", "")).strip()
        cmd = str(rule.get("next_command", "")).strip()
        if hint:
            fix_hints.append(hint)
        if cmd:
            next_commands.append(cmd)

    fix_hints.extend(compile_fix_hints)
    next_commands.extend(compile_next_commands)
    # keep deterministic order and deduplicate
    fix_hints = sorted(set(fix_hints))
    next_commands = sorted(set(next_commands))

    overall_ok = all(step["status"] == "OK" for step in steps) and compile_error_count == 0
    summary = {
        "schema": "IL_DOCTOR_REPORT_v1",
        "status": "OK" if overall_ok else "ERROR",
        "out_dir": str(out_dir),
        "steps": steps,
        "compile_health": compile_health,
        "fix_hints": fix_hints,
        "next_commands": next_commands,
    }
    (out_dir / "il.doctor.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if overall_ok:
        print("OK: il_doctor_summary status=OK")
        return 0
    print("ERROR: il_doctor_summary status=ERROR")
    return 1


def main(argv: List[str]) -> int:
    out, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run_doctor(out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
