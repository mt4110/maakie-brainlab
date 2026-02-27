#!/usr/bin/env python3
"""
S26-01 provider canary runner.

Goal:
- Fix timeout/retry/circuit policy as contract.
- Run real-provider canary cases in stopless mode.
- Persist JSON/Markdown evidence for PR body and CI artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CONFIG = "docs/ops/S26-01_PROVIDER_CANARY.toml"
DEFAULT_OUT_DIR = "docs/evidence/s26-01"
DEFAULT_TIMEOUT_SEC = 15

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_MISSING_PROVIDER_ENV = "MISSING_PROVIDER_ENV"
REASON_REQUESTS_UNAVAILABLE = "REQUESTS_UNAVAILABLE"
REASON_TIMEOUT = "TIMEOUT"
REASON_NETWORK_ERROR = "NETWORK_ERROR"
REASON_HTTP_429 = "HTTP_429"
REASON_HTTP_5XX = "HTTP_5XX"
REASON_HTTP_4XX = "HTTP_4XX"
REASON_AUTH_ERROR = "AUTH_ERROR"
REASON_BAD_RESPONSE = "BAD_RESPONSE"
REASON_ASSERTION_FAILED = "ASSERTION_FAILED"
REASON_CIRCUIT_OPEN = "CIRCUIT_OPEN"


RequestResult = Dict[str, Any]
Requester = Callable[[str, Dict[str, str], Dict[str, Any], int], RequestResult]


def _read_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("tomllib unavailable")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _policy_hash(policy: Dict[str, Any]) -> str:
    blob = json.dumps(policy, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    rel_text = rel.as_posix()
    if ".." in Path(rel_text).parts:
        return ""
    return rel_text


def classify_http_reason(status_code: int) -> str:
    if status_code in (401, 403):
        return REASON_AUTH_ERROR
    if status_code == 429:
        return REASON_HTTP_429
    if 500 <= status_code <= 599:
        return REASON_HTTP_5XX
    if 400 <= status_code <= 499:
        return REASON_HTTP_4XX
    return REASON_BAD_RESPONSE


def validate_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if str(cfg.get("schema_version") or "") != "s26-provider-canary-v1":
        return False, "schema_version mismatch"

    provider = cfg.get("provider")
    policy = cfg.get("policy")
    rollback = cfg.get("rollback")
    cases = cfg.get("cases")

    if not isinstance(provider, dict):
        return False, "provider missing"
    for key in ("id", "base_url_env", "api_key_env", "model_env", "path"):
        if not str(provider.get(key) or "").strip():
            return False, f"provider.{key} missing"

    if not isinstance(policy, dict):
        return False, "policy missing"
    for key in ("timeout_sec", "max_retries", "retry_backoff_ms", "jitter_ms", "circuit_open_sec", "max_inflight"):
        try:
            value = int(policy.get(key))
            if value < 0:
                return False, f"policy.{key} must be >= 0"
        except Exception:
            return False, f"policy.{key} invalid"
    if int(policy.get("timeout_sec", 0)) <= 0:
        return False, "policy.timeout_sec must be > 0"
    if int(policy.get("max_inflight", 0)) <= 0:
        return False, "policy.max_inflight must be > 0"
    if int(policy.get("max_inflight", 0)) != 1:
        return False, "policy.max_inflight must be 1 (serial runner)"

    retryable = policy.get("retryable_reason_codes")
    non_retryable = policy.get("non_retryable_reason_codes")
    if not isinstance(retryable, list) or not retryable:
        return False, "policy.retryable_reason_codes missing"
    if not isinstance(non_retryable, list) or not non_retryable:
        return False, "policy.non_retryable_reason_codes missing"
    retryable_set = {str(x) for x in retryable}
    non_retryable_set = {str(x) for x in non_retryable}
    if retryable_set & non_retryable_set:
        return False, "policy retryable/non_retryable overlap"

    if not isinstance(rollback, dict):
        return False, "rollback missing"
    if not str(rollback.get("command") or "").strip():
        return False, "rollback.command missing"

    if not isinstance(cases, list) or not cases:
        return False, "cases missing"
    seen = set()
    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            return False, f"cases[{idx}] invalid"
        case_id = str(case.get("id") or "").strip()
        prompt = str(case.get("prompt") or "").strip()
        if not case_id:
            return False, f"cases[{idx}].id missing"
        if case_id in seen:
            return False, f"cases[{idx}].id duplicated"
        seen.add(case_id)
        if not prompt:
            return False, f"cases[{idx}].prompt missing"
        if "must_pass" not in case:
            return False, f"cases[{idx}].must_pass missing"
        if not isinstance(case.get("must_pass"), bool):
            return False, f"cases[{idx}].must_pass invalid"
    return True, ""


def resolve_provider_runtime(provider_cfg: Dict[str, Any], env: Dict[str, str]) -> Dict[str, Any]:
    base_url = env.get(str(provider_cfg.get("base_url_env") or ""), "").strip()
    api_key = env.get(str(provider_cfg.get("api_key_env") or ""), "").strip()
    model = env.get(str(provider_cfg.get("model_env") or ""), "").strip()
    missing = []
    if not base_url:
        missing.append("base_url")
    if not api_key:
        missing.append("api_key")
    if not model:
        missing.append("model")
    return {
        "provider_id": str(provider_cfg.get("id") or ""),
        "base_url": base_url.rstrip("/"),
        "api_key": api_key,
        "model": model,
        "path": str(provider_cfg.get("path") or "/v1/chat/completions"),
        "missing": missing,
    }


def sanitize_runtime(runtime: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(runtime)
    key = str(out.get("api_key") or "")
    out["api_key_set"] = bool(key)
    out["api_key"] = "***" if key else ""
    return out


def requests_requester(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout_sec: int) -> RequestResult:
    if requests is None:
        return {"ok": False, "timeout": False, "status_code": 0, "json": None, "text": "", "error": "requests unavailable"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=max(1, timeout_sec))
    except requests.Timeout as exc:  # type: ignore[attr-defined]
        return {"ok": False, "timeout": True, "status_code": 0, "json": None, "text": "", "error": str(exc)}
    except requests.RequestException as exc:  # type: ignore[attr-defined]
        return {"ok": False, "timeout": False, "status_code": 0, "json": None, "text": "", "error": str(exc)}

    try:
        body = resp.json()
    except Exception:
        body = None
    return {
        "ok": True,
        "timeout": False,
        "status_code": int(resp.status_code),
        "json": body,
        "text": str(resp.text or ""),
        "error": "",
    }


def extract_content(result_json: Any) -> str:
    if not isinstance(result_json, dict):
        return ""
    choices = result_json.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    return str(message.get("content") or "")


def should_retry(reason_code: str, retryable_codes: List[str], non_retryable_codes: List[str]) -> bool:
    retryable = {str(x) for x in retryable_codes}
    non_retryable = {str(x) for x in non_retryable_codes}
    if reason_code in non_retryable:
        return False
    return reason_code in retryable


def run_case_with_retry(
    *,
    case: Dict[str, Any],
    runtime: Dict[str, Any],
    policy: Dict[str, Any],
    requester: Requester,
    circuit_state: Dict[str, float],
    now_fn: Callable[[], float] = time.time,
    sleep_fn: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> Dict[str, Any]:
    now = float(now_fn())
    open_until = float(circuit_state.get("open_until", 0.0))
    if open_until > now:
        return {
            "case_id": str(case.get("id") or ""),
            "status": "SKIP",
            "reason_code": REASON_CIRCUIT_OPEN,
            "attempts": [],
            "response_text": "",
            "http_status": 0,
            "error": f"circuit_open_until={open_until}",
        }

    retryable_codes = [str(x) for x in policy.get("retryable_reason_codes", [])]
    non_retryable_codes = [str(x) for x in policy.get("non_retryable_reason_codes", [])]
    timeout_sec = int(policy.get("timeout_sec", DEFAULT_TIMEOUT_SEC))
    max_retries = int(policy.get("max_retries", 0))
    backoff_ms = int(policy.get("retry_backoff_ms", 0))
    jitter_ms = int(policy.get("jitter_ms", 0))
    circuit_open_sec = int(policy.get("circuit_open_sec", 0))
    max_attempts = 1 + max(0, max_retries)
    local_rng = rng or random.Random(0)

    url = str(runtime.get("base_url") or "") + str(runtime.get("path") or "")
    headers = {
        "Authorization": f"Bearer {runtime.get('api_key', '')}",
        "Content-Type": "application/json",
    }
    prompt = str(case.get("prompt") or "")
    expect_substring = str(case.get("expect_substring") or "")
    payload = {
        "model": str(runtime.get("model") or ""),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    attempts: List[Dict[str, Any]] = []
    final_reason = ""
    final_error = ""
    final_text = ""
    final_status = 0
    for attempt_index in range(1, max_attempts + 1):
        started = now_fn()
        req = requester(url, headers, payload, timeout_sec)
        elapsed_ms = int(max(0.0, now_fn() - started) * 1000)
        reason_code = ""
        http_status = int(req.get("status_code") or 0)
        error = str(req.get("error") or "")
        text = ""
        status = "FAIL"

        if bool(req.get("timeout")):
            reason_code = REASON_TIMEOUT
        elif not bool(req.get("ok")):
            reason_code = REASON_NETWORK_ERROR
        elif 200 <= http_status <= 299:
            text = extract_content(req.get("json"))
            if not text:
                reason_code = REASON_BAD_RESPONSE
            elif expect_substring and expect_substring not in text:
                reason_code = REASON_ASSERTION_FAILED
            else:
                status = "PASS"
        else:
            reason_code = classify_http_reason(http_status)

        attempts.append(
            {
                "attempt": attempt_index,
                "status": status,
                "reason_code": reason_code,
                "http_status": http_status,
                "elapsed_ms": elapsed_ms,
                "error": error,
            }
        )

        if status == "PASS":
            return {
                "case_id": str(case.get("id") or ""),
                "status": "PASS",
                "reason_code": "",
                "attempts": attempts,
                "response_text": text,
                "http_status": http_status,
                "error": "",
            }

        final_reason = reason_code
        final_error = error
        final_text = text
        final_status = http_status

        retry = should_retry(reason_code, retryable_codes, non_retryable_codes)
        if retry and attempt_index < max_attempts:
            backoff = (backoff_ms / 1000.0) * attempt_index
            if jitter_ms > 0:
                backoff += local_rng.uniform(0.0, jitter_ms / 1000.0)
            if backoff > 0:
                sleep_fn(backoff)
            continue
        break

    if should_retry(final_reason, retryable_codes, non_retryable_codes) and circuit_open_sec > 0:
        circuit_state["open_until"] = now_fn() + float(circuit_open_sec)

    return {
        "case_id": str(case.get("id") or ""),
        "status": "FAIL",
        "reason_code": final_reason or REASON_BAD_RESPONSE,
        "attempts": attempts,
        "response_text": final_text,
        "http_status": final_status,
        "error": final_error,
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    lines: List[str] = []
    lines.append("# S26-01 Provider Canary (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- Config: `{payload.get('config_path', '')}`")
    lines.append(f"- PolicyHash: `{payload.get('policy', {}).get('hash', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- overall_status: `{summary.get('status', '')}`")
    lines.append(f"- passed_cases: `{summary.get('passed_cases', 0)}`")
    lines.append(f"- failed_cases: `{summary.get('failed_cases', 0)}`")
    lines.append(f"- skipped_cases: `{summary.get('skipped_cases', 0)}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append("")
    lines.append("## Rollback")
    lines.append("")
    lines.append(f"- command: `{payload.get('rollback', {}).get('command', '')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-01 Provider Canary")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- passed_failed_skipped: {summary.get('passed_cases', 0)}/{summary.get('failed_cases', 0)}/{summary.get('skipped_cases', 0)}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- policy_hash: {payload.get('policy', {}).get('hash', '')}")
    lines.append(f"- rollback: {payload.get('rollback', {}).get('command', '')}")
    lines.append(f"- artifact: docs/evidence/s26-01/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure_artifacts(
    *,
    repo_root: Path,
    out_dir: Path,
    config_path: Path,
    reason_code: str,
    errors: List[str],
) -> None:
    payload = {
        "schema_version": "s26-provider-canary-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])},
        "config_path": to_repo_rel(repo_root, config_path),
        "policy": {"hash": "", "value": {}},
        "provider": {"provider_id": "", "base_url": "", "api_key": "", "model": "", "path": "", "missing": [], "api_key_set": False},
        "cases": [],
        "summary": {
            "status": "FAIL",
            "passed_cases": 0,
            "failed_cases": 0,
            "skipped_cases": 0,
            "reason_code": reason_code,
            "errors": list(errors),
        },
        "rollback": {"command": ""},
        "artifact_names": {"json": "provider_canary_latest.json", "md": "provider_canary_latest.md"},
    }
    json_path = out_dir / "provider_canary_latest.json"
    md_path = out_dir / "provider_canary_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--timeout-sec", type=int, default=0, help="Override policy timeout when >0")
    parser.add_argument("--strict-provider-env", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-provider-canary", obs_root=args.obs_root)

    config_path = (repo_root / args.config).resolve()
    if not config_path.exists():
        emit("ERROR", f"config missing path={config_path}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"config missing path={config_path}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cfg = _read_toml(config_path)
    except Exception as exc:
        emit("ERROR", f"config parse failed err={exc}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"config parse failed err={exc}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    ok, reason = validate_config(cfg)
    if not ok:
        emit("ERROR", f"config invalid reason={reason}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"config invalid reason={reason}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    emit("OK", f"config={config_path}", events)

    policy = dict(cfg.get("policy", {}))
    if int(args.timeout_sec) > 0:
        policy["timeout_sec"] = int(args.timeout_sec)
    provider_cfg = dict(cfg.get("provider", {}))
    runtime = resolve_provider_runtime(provider_cfg, env=dict(os.environ))

    if runtime.get("missing"):
        missing = ",".join(runtime.get("missing", []))
        msg = f"provider env missing={missing}; canary skipped"
        if args.strict_provider_env:
            emit("ERROR", msg, events)
            write_failure_artifacts(
                repo_root=repo_root,
                out_dir=out_dir,
                config_path=config_path,
                reason_code=REASON_MISSING_PROVIDER_ENV,
                errors=[msg],
            )
            write_events(run_dir, events)
            write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_MISSING_PROVIDER_ENV})
            return 1
        emit("WARN", msg, events)
        payload = {
            "schema_version": "s26-provider-canary-result-v1",
            "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])},
            "config_path": to_repo_rel(repo_root, config_path),
            "policy": {"hash": _policy_hash(policy), "value": policy},
            "provider": sanitize_runtime(runtime),
            "cases": [],
            "summary": {
                "status": "SKIP",
                "passed_cases": 0,
                "failed_cases": 0,
                "skipped_cases": int(len(cfg.get("cases", []))),
                "reason_code": REASON_MISSING_PROVIDER_ENV,
            },
            "rollback": {"command": str(dict(cfg.get("rollback", {})).get("command") or "")},
            "artifact_names": {"json": "provider_canary_latest.json", "md": "provider_canary_latest.md"},
        }
        json_path = out_dir / "provider_canary_latest.json"
        md_path = out_dir / "provider_canary_latest.md"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(build_markdown(payload), encoding="utf-8")
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "SKIP", "reason_code": REASON_MISSING_PROVIDER_ENV})
        emit("OK", f"artifact_json={json_path}", events)
        emit("OK", f"artifact_md={md_path}", events)
        return 0

    if requests is None:
        emit("WARN", "requests unavailable; canary skipped", events)
        payload = {
            "schema_version": "s26-provider-canary-result-v1",
            "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])},
            "config_path": to_repo_rel(repo_root, config_path),
            "policy": {"hash": _policy_hash(policy), "value": policy},
            "provider": sanitize_runtime(runtime),
            "cases": [],
            "summary": {
                "status": "SKIP",
                "passed_cases": 0,
                "failed_cases": 0,
                "skipped_cases": int(len(cfg.get("cases", []))),
                "reason_code": REASON_REQUESTS_UNAVAILABLE,
            },
            "rollback": {"command": str(dict(cfg.get("rollback", {})).get("command") or "")},
            "artifact_names": {"json": "provider_canary_latest.json", "md": "provider_canary_latest.md"},
        }
        json_path = out_dir / "provider_canary_latest.json"
        md_path = out_dir / "provider_canary_latest.md"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(build_markdown(payload), encoding="utf-8")
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "SKIP", "reason_code": REASON_REQUESTS_UNAVAILABLE})
        emit("OK", f"artifact_json={json_path}", events)
        emit("OK", f"artifact_md={md_path}", events)
        return 0

    cases = list(cfg.get("cases", []))
    circuit_state: Dict[str, float] = {"open_until": 0.0}
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    passed = 0
    failed = 0
    skipped = 0

    for case in cases:
        out = run_case_with_retry(
            case=case,
            runtime=runtime,
            policy=policy,
            requester=requests_requester,
            circuit_state=circuit_state,
        )
        results.append(out)
        state = str(out.get("status") or "FAIL")
        if state == "PASS":
            passed += 1
            emit("OK", f"case={out.get('case_id')} status=PASS attempts={len(out.get('attempts', []))}", events)
            continue
        if state == "SKIP":
            skipped += 1
            emit("WARN", f"case={out.get('case_id')} status=SKIP reason={out.get('reason_code')}", events)
            continue
        failed += 1
        emit("ERROR", f"case={out.get('case_id')} status=FAIL reason={out.get('reason_code')}", events)
        if bool(case.get("must_pass", False)):
            errors.append(f"must_pass case failed id={out.get('case_id')}")

    reason_code = ""
    if errors:
        reason_code = str(next((r.get("reason_code") for r in results if r.get("status") == "FAIL"), REASON_BAD_RESPONSE))
    status = "PASS" if not errors else "FAIL"
    rollback = dict(cfg.get("rollback", {}))
    payload = {
        "schema_version": "s26-provider-canary-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])},
        "config_path": to_repo_rel(repo_root, config_path),
        "policy": {"hash": _policy_hash(policy), "value": policy},
        "provider": sanitize_runtime(runtime),
        "cases": results,
        "summary": {
            "status": status,
            "passed_cases": passed,
            "failed_cases": failed,
            "skipped_cases": skipped,
            "reason_code": reason_code,
        },
        "rollback": {"command": str(rollback.get("command") or "")},
        "artifact_names": {"json": "provider_canary_latest.json", "md": "provider_canary_latest.md"},
    }

    json_path = out_dir / "provider_canary_latest.json"
    md_path = out_dir / "provider_canary_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={json_path}", events)
    emit("OK", f"artifact_md={md_path}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
