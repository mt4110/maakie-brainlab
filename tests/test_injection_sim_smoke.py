# stopless smoke: no sys.exit / no SystemExit / no assert / do not raise to stop
from __future__ import annotations

import json
import os
import re
from typing import List, Tuple


SUITE_PATH = os.path.join("docs", "ops", "INJECTION_SIM_SUITE_v1.md")


def _print_ok(msg: str) -> None:
    print(f"OK: {msg}")


def _print_skip(msg: str) -> None:
    print(f"SKIP: {msg}")


def _print_err(msg: str) -> None:
    print(f"ERROR: {msg}")


def _read_text(path: str) -> Tuple[bool, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return True, f.read()
    except Exception as e:
        _print_err(f"cannot_read path={path} err={type(e).__name__}")
        return False, ""


def _extract_fixtures(md: str) -> List[str]:
    # Accept both:
    #   - fixture: relative/path.json
    #   - fixture: (optional) relative/path.json
    out: List[str] = []
    for line in md.splitlines():
        m = re.match(r"^\s*-\s*fixture:\s*(.+?)\s*$", line)
        if not m:
            continue
        raw = m.group(1).strip()
        raw = re.sub(r"^\(optional\)\s*", "", raw).strip()
        if raw in ("(none)", "none", ""):
            continue
        out.append(raw)
    return out


def _is_relative_path(p: str) -> bool:
    if p.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:[\\/]", p):  # Windows drive path
        return False
    if ".." in p.split("/"):
        return False
    return True


def _check_json_file(path: str) -> bool:
    ok = True
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        _print_ok(f"json_parse path={path}")
    except Exception as e:
        _print_err(f"json_parse_failed path={path} err={type(e).__name__}")
        ok = False
    return ok


def _check_jsonl_file(path: str, max_lines: int = 200) -> bool:
    ok = True
    n = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                n += 1
                if n > max_lines:
                    _print_skip(f"jsonl_truncated path={path} lines_checked={max_lines}")
                    break
                s = line.strip()
                if s == "":
                    continue
                try:
                    json.loads(s)
                except Exception as e:
                    _print_err(f"jsonl_line_parse_failed path={path} line={n} err={type(e).__name__}")
                    ok = False
                    # continue scanning lightly; do not raise
        _print_ok(f"jsonl_scan_done path={path} lines_seen={n}")
    except Exception as e:
        _print_err(f"jsonl_open_failed path={path} err={type(e).__name__}")
        ok = False
    return ok


def run_smoke() -> int:
    # return code is informational only; caller must not sys.exit
    ok_all = True

    if not os.path.exists(SUITE_PATH):
        _print_err(f"suite_missing path={SUITE_PATH}")
        return 0

    ok, md = _read_text(SUITE_PATH)
    if not ok:
        return 0

    if "INJECTION_SIM_SUITE_v1" not in md:
        _print_err("suite_header_missing marker=INJECTION_SIM_SUITE_v1")
        ok_all = False
    else:
        _print_ok("suite_header_present")

    fixtures = _extract_fixtures(md)
    if not fixtures:
        _print_skip("no_fixtures_declared")
        _print_ok("smoke_done")
        return 0

    _print_ok(f"fixtures_declared count={len(fixtures)}")

    for fx in fixtures:
        if not _is_relative_path(fx):
            _print_err(f"fixture_not_relative path={fx}")
            ok_all = False
            continue

        if not os.path.exists(fx):
            _print_err(f"fixture_missing path={fx}")
            ok_all = False
            continue

        if fx.endswith(".json"):
            if not _check_json_file(fx):
                ok_all = False
        elif fx.endswith(".jsonl"):
            if not _check_jsonl_file(fx):
                ok_all = False
        else:
            _print_skip(f"fixture_unknown_type path={fx}")

    if ok_all:
        _print_ok("smoke_summary result=OK")
    else:
        _print_err("smoke_summary result=ERROR_PRESENT (stopless)")

    return 0


if __name__ == "__main__":
    try:
        run_smoke()
    except Exception as e:
        # absolutely do not crash; log and end
        _print_err(f"unhandled_exception err={type(e).__name__}")
        _print_ok("smoke_done (stopless)")
