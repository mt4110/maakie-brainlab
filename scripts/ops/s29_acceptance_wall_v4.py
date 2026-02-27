#!/usr/bin/env python3
"""
S29-07 acceptance wall v5.

Goal:
- Evaluate acceptance cases with severity and fallback guidance.
- Distinguish hard-stop failures (critical) from soft warnings.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CASES_FILE = "docs/ops/S29-07_ACCEPTANCE_CASES_V5.json"
DEFAULT_OUT_DIR = "docs/evidence/s29-07"

SEVERITIES = {"critical", "major", "minor"}
ALLOWED_OPS = {"eq", "neq", "gte", "lte", "in", "contains", "truthy", "len_gte", "len_lte"}

REASON_CASE_INVALID = "CASE_INVALID"
REASON_CASES_FILE_INVALID = "CASES_FILE_INVALID"
REASON_FILE_MISSING = "FILE_MISSING"
REASON_JSON_INVALID = "JSON_INVALID"
REASON_PATH_MISSING = "PATH_MISSING"
REASON_ASSERTION_FAILED = "ASSERTION_FAILED"
REASON_ARTIFACT_PATH_UNSAFE = "ARTIFACT_PATH_UNSAFE"
REASON_ARTIFACT_OUTSIDE_REPO = "ARTIFACT_OUTSIDE_REPO"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    text = rel.as_posix()
    if ".." in Path(text).parts:
        return ""
    return text


def is_safe_rel_path(value: str) -> bool:
    p = Path(str(value or "").strip())
    if not str(p):
        return False
    if p.is_absolute():
        return False
    return ".." not in p.parts


def sanitize_token(raw: str, max_len: int = 64) -> str:
    text = str(raw or "").strip().lower()
    out: List[str] = []
    for ch in text:
        if ch.isalnum() or ch in {"_", "-", "."}:
            out.append(ch)
        else:
            out.append("_")
    compact = "".join(out).strip("._-")
    compact = "_".join(part for part in compact.split("_") if part)
    if not compact:
        return "case"
    return compact[:max_len]


def load_cases(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("cases file must be JSON object")
    schema = str(obj.get("schema_version") or "")
    rows = obj.get("cases")
    if not isinstance(rows, list) or not rows:
        raise ValueError("cases must be non-empty list")
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("cases must contain only objects")
        out.append(row)
    return schema, out


def validate_case(case: Dict[str, Any]) -> Tuple[bool, str]:
    if not str(case.get("id") or "").strip():
        return False, "id missing"
    if str(case.get("severity") or "") not in SEVERITIES:
        return False, "severity invalid"
    artifact = str(case.get("artifact") or "").strip()
    if not artifact:
        return False, "artifact missing"
    if not is_safe_rel_path(artifact):
        return False, "artifact path unsafe"
    assertion = case.get("assertion")
    if not isinstance(assertion, dict):
        return False, "assertion missing"
    op = str(assertion.get("op") or "").strip()
    if op not in ALLOWED_OPS:
        return False, f"assertion.op invalid: {op}"
    if op != "truthy" and "value" not in assertion:
        return False, "assertion.value missing"
    if op in {"len_gte", "len_lte"} and not str(assertion.get("path") or "").strip():
        return False, "assertion.path missing"
    if op not in {"truthy"} and not str(assertion.get("path") or "").strip():
        return False, "assertion.path missing"
    return True, ""


def normalize_severity(value: str, default: str = "critical") -> str:
    text = str(value or "").strip()
    if text in SEVERITIES:
        return text
    return default


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value))


def resolve_path(doc: Any, path: str) -> Tuple[bool, Any]:
    cur = doc
    parts = [p for p in str(path).split(".") if p]
    if not parts:
        return True, cur
    for part in parts:
        if isinstance(cur, dict):
            if part not in cur:
                return False, None
            cur = cur[part]
            continue
        if isinstance(cur, list):
            try:
                idx = int(part)
            except Exception:
                return False, None
            if idx < 0 or idx >= len(cur):
                return False, None
            cur = cur[idx]
            continue
        return False, None
    return True, cur


def evaluate_assertion(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "gte":
        try:
            return _to_float(actual) >= _to_float(expected)
        except Exception:
            return False
    if op == "lte":
        try:
            return _to_float(actual) <= _to_float(expected)
        except Exception:
            return False
    if op == "in":
        if not isinstance(expected, list):
            return False
        return actual in expected
    if op == "contains":
        return str(expected) in str(actual)
    if op == "truthy":
        return bool(actual)
    if op == "len_gte":
        try:
            return len(actual) >= int(expected)
        except Exception:
            return False
    if op == "len_lte":
        try:
            return len(actual) <= int(expected)
        except Exception:
            return False
    return False


def run_case(repo_root: Path, case: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    cid = str(case.get("id") or "")
    title = str(case.get("title") or cid)
    severity = str(case.get("severity") or "minor")
    fallback = str(case.get("fallback") or "")
    rel_artifact = str(case.get("artifact") or "")
    safe_cid = sanitize_token(cid)
    log_path = run_dir / f"{safe_cid}.log"
    lines: List[str] = [f"case={cid}", f"severity={severity}", f"artifact={rel_artifact}"]

    if not is_safe_rel_path(rel_artifact):
        reason = REASON_ARTIFACT_PATH_UNSAFE
        lines.append(f"result=FAIL reason={reason}")
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {
            "case_id": cid,
            "title": title,
            "severity": severity,
            "fallback": fallback,
            "status": "FAIL",
            "reason_code": reason,
            "artifact": rel_artifact,
            "assertion": dict(case.get("assertion") or {}),
            "actual": None,
            "log_path": str(log_path.name),
        }

    artifact_path = (repo_root / rel_artifact).resolve()
    if repo_root.resolve() not in artifact_path.parents and artifact_path != repo_root.resolve():
        reason = REASON_ARTIFACT_OUTSIDE_REPO
        lines.append(f"result=FAIL reason={reason}")
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {
            "case_id": cid,
            "title": title,
            "severity": severity,
            "fallback": fallback,
            "status": "FAIL",
            "reason_code": reason,
            "artifact": rel_artifact,
            "assertion": dict(case.get("assertion") or {}),
            "actual": None,
            "log_path": str(log_path.name),
        }

    assertion = dict(case.get("assertion") or {})
    op = str(assertion.get("op") or "")
    path = str(assertion.get("path") or "")
    lines.extend([f"op={op}", f"path={path}"])

    if not artifact_path.exists():
        reason = REASON_FILE_MISSING
        lines.append(f"result=FAIL reason={reason}")
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {
            "case_id": cid,
            "title": title,
            "severity": severity,
            "fallback": fallback,
            "status": "FAIL",
            "reason_code": reason,
            "artifact": rel_artifact,
            "assertion": assertion,
            "actual": None,
            "log_path": str(log_path.name),
        }

    try:
        doc = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as exc:
        reason = REASON_JSON_INVALID
        lines.append(f"result=FAIL reason={reason} err={exc}")
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {
            "case_id": cid,
            "title": title,
            "severity": severity,
            "fallback": fallback,
            "status": "FAIL",
            "reason_code": reason,
            "artifact": rel_artifact,
            "assertion": assertion,
            "actual": None,
            "log_path": str(log_path.name),
        }

    actual: Any = doc
    use_path = bool(path) and (op != "truthy" or bool(path))
    if use_path:
        ok, resolved = resolve_path(doc, path)
        if not ok:
            reason = REASON_PATH_MISSING
            lines.append(f"result=FAIL reason={reason}")
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return {
                "case_id": cid,
                "title": title,
                "severity": severity,
                "fallback": fallback,
                "status": "FAIL",
                "reason_code": reason,
                "artifact": rel_artifact,
                "assertion": assertion,
                "actual": None,
                "log_path": str(log_path.name),
            }
        actual = resolved

    expected = assertion.get("value")
    passed = evaluate_assertion(actual, op, expected)
    status = "PASS" if passed else "FAIL"
    reason = "" if passed else REASON_ASSERTION_FAILED
    lines.append(f"actual={actual}")
    lines.append(f"expected={expected}")
    lines.append(f"result={status} reason={reason or '-'}")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "case_id": cid,
        "title": title,
        "severity": severity,
        "fallback": fallback,
        "status": status,
        "reason_code": reason,
        "artifact": rel_artifact,
        "assertion": assertion,
        "actual": actual,
        "log_path": str(log_path.name),
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    lines: List[str] = []
    lines.append("# S29-07 Acceptance Wall v5 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- CasesFile: `{payload.get('cases_file', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- acceptance: `{summary.get('passed_cases', 0)}/{summary.get('total_cases', 0)}`")
    lines.append(f"- critical_failed: `{summary.get('critical_failed', 0)}`")
    lines.append("")
    lines.append("## Severity Failures")
    lines.append("")
    for sev, cnt in dict(summary.get("severity_failed", {})).items():
        lines.append(f"- {sev}: `{cnt}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S29-07 Acceptance Wall v5")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- acceptance: {summary.get('passed_cases', 0)}/{summary.get('total_cases', 0)}")
    lines.append(f"- critical_failed: {summary.get('critical_failed', 0)}")
    lines.append(f"- severity_failed: {summary.get('severity_failed', {})}")
    lines.append(f"- artifact: docs/evidence/s29-07/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure(out_dir: Path, repo_root: Path, cases_path: Path, reason_code: str, message: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": "s29-acceptance-wall-v5",
        "captured_at_utc": utc_now().isoformat(),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])} ,
        "cases_file": to_repo_rel(repo_root, cases_path),
        "summary": {
            "status": "FAIL",
            "reason_code": reason_code,
            "total_cases": 1,
            "passed_cases": 0,
            "failed_cases": 1,
            "critical_failed": 1,
            "severity_failed": {"critical": 1, "major": 0, "minor": 0},
            "failure_counts": {reason_code: 1},
        },
        "cases": [
            {
                "case_id": "load_cases",
                "title": "load acceptance cases",
                "severity": "critical",
                "fallback": "",
                "status": "FAIL",
                "reason_code": reason_code,
                "artifact": to_repo_rel(repo_root, cases_path),
                "assertion": {},
                "actual": message,
                "log_path": "",
            }
        ],
        "artifact_names": {"json": "acceptance_wall_v5_latest.json", "md": "acceptance_wall_v5_latest.md", "run_dir": ""},
    }
    out_json = out_dir / "acceptance_wall_v5_latest.json"
    out_md = out_dir / "acceptance_wall_v5_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-file", default=DEFAULT_CASES_FILE)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s29-acceptance-wall-v5", obs_root=args.obs_root)

    cases_path = (repo_root / args.cases_file).resolve()
    if not cases_path.exists():
        emit("ERROR", f"cases file missing path={cases_path}", events)
        write_failure(out_dir, repo_root, cases_path, REASON_CASE_INVALID, f"cases file missing path={cases_path}")
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CASE_INVALID})
        return 1

    try:
        schema, cases = load_cases(cases_path)
    except Exception as exc:
        emit("ERROR", f"cases file parse failed err={exc}", events)
        write_failure(out_dir, repo_root, cases_path, REASON_CASES_FILE_INVALID, str(exc))
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CASES_FILE_INVALID})
        return 1
    emit("OK", f"cases_loaded={len(cases)} schema={schema}", events)

    rows: List[Dict[str, Any]] = []
    failure_counts: Dict[str, int] = {}
    severity_failed = {"critical": 0, "major": 0, "minor": 0}
    status = "PASS"

    for case in cases:
        valid, reason = validate_case(case)
        cid = str(case.get("id") or "")
        if not valid:
            emit("ERROR", f"case={cid or '?'} invalid reason={reason}", events)
            out = {
                "case_id": cid or "invalid-case",
                "title": str(case.get("title") or cid or "invalid-case"),
                "severity": normalize_severity(str(case.get("severity") or "critical"), default="critical"),
                "fallback": str(case.get("fallback") or ""),
                "status": "FAIL",
                "reason_code": REASON_CASE_INVALID,
                "artifact": str(case.get("artifact") or ""),
                "assertion": dict(case.get("assertion") or {}),
                "actual": None,
                "log_path": "",
            }
        else:
            out = run_case(repo_root=repo_root, case=case, run_dir=run_dir)
            level = "OK" if out["status"] == "PASS" else "ERROR"
            emit(level, f"case={out['case_id']} {out['status']} severity={out['severity']} reason={out['reason_code'] or '-'}", events)

        if out["status"] == "FAIL":
            reason_code = str(out.get("reason_code") or REASON_ASSERTION_FAILED)
            severity = normalize_severity(str(out.get("severity") or "minor"), default="minor")
            failure_counts[reason_code] = int(failure_counts.get(reason_code, 0)) + 1
            severity_failed[severity] = int(severity_failed.get(severity, 0)) + 1
            if severity == "critical":
                status = "FAIL"
            elif status == "PASS":
                status = "WARN"

        rows.append(out)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = total - passed
    summary_reason = ""
    if status != "PASS":
        summary_reason = next((r.get("reason_code") for r in rows if r.get("status") == "FAIL" and r.get("reason_code")), "")

    payload: Dict[str, Any] = {
        "schema_version": "s29-acceptance-wall-v5",
        "captured_at_utc": utc_now().isoformat(),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])} ,
        "cases_file": to_repo_rel(repo_root, cases_path),
        "summary": {
            "status": status,
            "reason_code": summary_reason,
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": failed,
            "critical_failed": int(severity_failed.get("critical", 0)),
            "severity_failed": severity_failed,
            "failure_counts": failure_counts,
        },
        "cases": rows,
        "artifact_names": {
            "json": "acceptance_wall_v5_latest.json",
            "md": "acceptance_wall_v5_latest.md",
            "run_dir": to_repo_rel(repo_root, run_dir),
        },
    }

    out_json = out_dir / "acceptance_wall_v5_latest.json"
    out_md = out_dir / "acceptance_wall_v5_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": summary_reason, "critical_failed": severity_failed.get("critical", 0)})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
