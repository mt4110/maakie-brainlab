#!/usr/bin/env python3
"""
S28-03 readiness notification dispatcher.

Goal:
- Build consistent readiness message payload for ops channel.
- Optionally deliver payload to webhook while keeping non-blocking behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_OUT_DIR = "docs/evidence/s28-03"
DEFAULT_READINESS = "docs/evidence/s28-09/slo_readiness_v2_latest.json"
DEFAULT_READINESS_FALLBACK = "docs/evidence/s27-09/slo_readiness_latest.json"
DEFAULT_SCHEDULE = "docs/evidence/s27-03/release_readiness_schedule_latest.json"

REASON_READINESS_MISSING = "READINESS_MISSING"
REASON_NOTIFY_DRY_RUN = "NOTIFY_DRY_RUN"
REASON_WEBHOOK_NOT_CONFIGURED = "WEBHOOK_NOT_CONFIGURED"
REASON_NOTIFY_SEND_FAILED = "NOTIFY_SEND_FAILED"


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


def read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def resolve_primary_or_fallback(primary: Path, fallback: Path) -> tuple[Dict[str, Any], Path, bool]:
    primary_doc = read_json_if_exists(primary)
    if primary_doc:
        return primary_doc, primary, False
    fallback_doc = read_json_if_exists(fallback)
    if fallback_doc:
        return fallback_doc, fallback, True
    return {}, primary, False


def compose_message(channel: str, readiness: Dict[str, Any], schedule: Dict[str, Any]) -> str:
    rs = dict(readiness.get("summary", {}))
    ss = dict(schedule.get("summary", {}))
    lines = [
        f"[Ops Readiness] channel={channel}",
        f"readiness={rs.get('readiness', '')}",
        f"status={rs.get('status', '')}",
        f"reason={rs.get('reason_code', '')}",
        f"blocked_total={rs.get('blocked_total', rs.get('blocked_gates', 0))}",
        f"schedule_status={ss.get('status', '')}",
        f"schedule_reason={ss.get('reason_code', '')}",
    ]
    return " | ".join(lines)


def post_webhook(url: str, payload: Dict[str, Any], timeout_sec: int) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=max(1, int(timeout_sec))) as resp:
            status = int(resp.status)
            text = (resp.read() or b"").decode("utf-8", errors="ignore")
            return {
                "sent": 200 <= status < 300,
                "http_status": status,
                "response_tail": text[-600:],
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        data = exc.read() if hasattr(exc, "read") else b""
        text = data.decode("utf-8", errors="ignore")
        return {
            "sent": False,
            "http_status": int(getattr(exc, "code", 0) or 0),
            "response_tail": text[-600:],
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "sent": False,
            "http_status": 0,
            "response_tail": "",
            "error": str(exc),
        }


def deliver_with_retries(
    send_once,
    *,
    max_retries: int,
    retry_backoff_sec: float,
    sleep_fn=time.sleep,
) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    retry_n = max(0, int(max_retries))
    backoff = max(0.0, float(retry_backoff_sec))

    final = {"sent": False, "http_status": 0, "response_tail": "", "error": ""}
    for idx in range(retry_n + 1):
        current = dict(send_once())
        current["attempt"] = idx + 1
        attempts.append(current)
        final = current
        if bool(current.get("sent")):
            break
        if idx < retry_n and backoff > 0:
            sleep_fn(backoff)

    return {
        "sent": bool(final.get("sent")),
        "http_status": int(final.get("http_status", 0) or 0),
        "response_tail": str(final.get("response_tail", ""))[-600:],
        "error": str(final.get("error", "")),
        "attempt_count": len(attempts),
        "attempts": attempts,
    }


def compute_delivery_rate(*, sent: bool, attempt_count: int, attempted: bool) -> float | None:
    attempts = max(0, int(attempt_count))
    if attempts > 0:
        return round((1 if sent else 0) / float(attempts), 4)
    if attempted:
        return 1.0 if sent else 0.0
    return None


def delivery_state(*, sent: bool, attempt_count: int, attempted: bool) -> str:
    if sent:
        return "SENT"
    if max(0, int(attempt_count)) > 0 or attempted:
        return "FAILED"
    return "NOT_ATTEMPTED"


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    notify = dict(payload.get("notification", {}))
    lines: List[str] = []
    lines.append("# S28-03 Readiness Notify (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- notify_sent: `{notify.get('sent', False)}`")
    lines.append(f"- delivery_state: `{notify.get('delivery_state', '')}`")
    lines.append(f"- delivery_rate: `{notify.get('delivery_rate', None)}`")
    lines.append(f"- channel: `{payload.get('channel', '')}`")
    lines.append("")
    lines.append("## Message")
    lines.append("")
    lines.append(f"- payload: `{payload.get('message', '')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S28-03 Readiness Notify")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- notify_sent: {notify.get('sent', False)}")
    lines.append(f"- channel: {payload.get('channel', '')}")
    lines.append(f"- artifact: docs/evidence/s28-03/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--readiness-json", default=DEFAULT_READINESS)
    parser.add_argument("--readiness-fallback-json", default=DEFAULT_READINESS_FALLBACK)
    parser.add_argument("--schedule-json", default=DEFAULT_SCHEDULE)
    parser.add_argument("--channel", default="#ops-release")
    parser.add_argument("--webhook-env", default="S28_READINESS_WEBHOOK_URL")
    parser.add_argument("--timeout-sec", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-backoff-sec", type=float, default=1.0)
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s28-readiness-notify", obs_root=args.obs_root)

    readiness_path = (repo_root / str(args.readiness_json)).resolve()
    readiness_fallback_path = (repo_root / str(args.readiness_fallback_json)).resolve()
    schedule_path = (repo_root / str(args.schedule_json)).resolve()
    readiness, readiness_resolved_path, used_fallback = resolve_primary_or_fallback(readiness_path, readiness_fallback_path)
    schedule = read_json_if_exists(schedule_path)

    status = "PASS"
    reason_code = ""
    if not readiness:
        status = "FAIL"
        reason_code = REASON_READINESS_MISSING
        emit("ERROR", f"readiness missing primary={readiness_path} fallback={readiness_fallback_path}", events)
    elif used_fallback:
        emit("WARN", f"readiness fallback used path={readiness_fallback_path}", events)

    message = compose_message(str(args.channel), readiness, schedule)
    notify = {
        "attempted": bool(args.send),
        "sent": False,
        "http_status": 0,
        "response_tail": "",
        "error": "",
        "attempt_count": 0,
        "attempts": [],
        "delivery_rate": None,
        "delivery_state": "NOT_ATTEMPTED",
    }

    webhook_url = str(os.environ.get(str(args.webhook_env), "") or "")
    if status != "FAIL":
        if not args.send:
            status = "WARN"
            reason_code = REASON_NOTIFY_DRY_RUN
            emit("WARN", "notification dry-run (use --send to deliver)", events)
        elif not webhook_url:
            status = "WARN"
            reason_code = REASON_WEBHOOK_NOT_CONFIGURED
            emit("WARN", f"webhook env not configured env={args.webhook_env}", events)
        else:
            notify_payload = {
                "channel": str(args.channel),
                "text": message,
                "meta": {
                    "tool": "s28-readiness-notify",
                    "branch": git_out(repo_root, ["branch", "--show-current"]),
                },
            }
            notify_result = deliver_with_retries(
                lambda: post_webhook(webhook_url, notify_payload, int(args.timeout_sec)),
                max_retries=int(args.max_retries),
                retry_backoff_sec=float(args.retry_backoff_sec),
            )
            notify = {**notify, **notify_result}
            if notify.get("sent"):
                status = "PASS"
                reason_code = ""
                emit(
                    "OK",
                    f"notification delivered status={notify.get('http_status')} attempts={notify.get('attempt_count', 0)}",
                    events,
                )
            else:
                status = "WARN"
                reason_code = REASON_NOTIFY_SEND_FAILED
                emit(
                    "WARN",
                    f"notification failed status={notify.get('http_status')} attempts={notify.get('attempt_count', 0)} err={notify.get('error')}",
                    events,
                )

    notify["delivery_rate"] = compute_delivery_rate(
        sent=bool(notify.get("sent")),
        attempt_count=int(notify.get("attempt_count", 0) or 0),
        attempted=bool(notify.get("attempted")),
    )
    notify["delivery_state"] = delivery_state(
        sent=bool(notify.get("sent")),
        attempt_count=int(notify.get("attempt_count", 0) or 0),
        attempted=bool(notify.get("attempted")),
    )

    payload: Dict[str, Any] = {
        "schema_version": "s28-readiness-notify-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "inputs": {
            "readiness_json": to_repo_rel(repo_root, readiness_resolved_path),
            "readiness_primary_json": to_repo_rel(repo_root, readiness_path),
            "readiness_fallback_json": to_repo_rel(repo_root, readiness_fallback_path),
            "readiness_fallback_used": used_fallback,
            "schedule_json": to_repo_rel(repo_root, schedule_path),
            "webhook_env": str(args.webhook_env),
            "send": bool(args.send),
            "max_retries": int(args.max_retries),
            "retry_backoff_sec": float(args.retry_backoff_sec),
        },
        "channel": str(args.channel),
        "message": message,
        "notification": notify,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "notify_sent": bool(notify.get("sent")),
            "readiness": str(dict(readiness.get("summary", {})).get("readiness") or ""),
        },
        "artifact_names": {
            "json": "readiness_notify_latest.json",
            "md": "readiness_notify_latest.md",
        },
    }

    out_json = out_dir / "readiness_notify_latest.json"
    out_md = out_dir / "readiness_notify_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "notify_sent": bool(notify.get("sent"))})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
