#!/usr/bin/env python3
"""
S22-08: Eval Wall v2 (IL-centered) — stopless runner (integrated)

Key properties:
- NO sys.exit / NO SystemExit / NO assert
- No control-flow by exit codes; decisions are based on output text + STOP flags.
- CPU-safe: streaming JSONL, segment timebox, per-case timeout, capped logs.
- Entry interface auto-discovery: runs `python3 scripts/il_entry.py --help` once (light),
  then prepares 3 strategies (positional / --in/--out / --input/--output),
  but tries at most 2 attempts (safety guard).

Output:
<OUT>/
  run.json, summary.json, SHA256SUMS.txt, audit.json
  cases/<case_id>/{result.json, entry_stdout.txt, entry_stderr.txt, case_input.json}

stdout:
- minimal line logs: OK:/ERROR:/SKIP: plus summary

Schemas:
- result.json schema_version: "s22-08-result-v1"
- run.json    schema_version: "s22-08-run-v1"
- summary.json schema_version: "s22-08-summary-v1"
- audit.json   schema_version: "s22-08-audit-v1"
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import glob as _glob
from datetime import datetime, timezone


# -------------------------
# Safe argparse (no exit)
# -------------------------
class SafeArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._safe_error = ""

    def exit(self, status=0, message=None):
        if message:
            self._safe_error = message.strip()

    def error(self, message):
        self._safe_error = str(message).strip()


# -------------------------
# Tiny utilities
# -------------------------
def now_utc_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_int(s, name, default):
    try:
        if s is None:
            return (True, default, "OK")
        v = int(str(s))
        return (True, v, "OK")
    except Exception:
        return (False, default, "int_parse_failed name=" + name)


def json_dump_atomic(path, obj):
    """
    Atomic-ish write: write temp then os.replace.
    Never raises. Returns (ok, note).
    """
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
    except Exception as e:
        return (False, "mkdir_failed err=" + e.__class__.__name__)

    tmp = path + ".tmp." + str(os.getpid()) + "." + str(int(time.time() * 1000))
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        try:
            os.replace(tmp, path)
        except Exception as e:
            try:
                os.remove(tmp)
            except Exception:
                pass
            return (False, "replace_failed err=" + e.__class__.__name__)
        return (True, "OK")
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return (False, "write_failed err=" + e.__class__.__name__)


def sha256_file(path):
    """
    Streaming sha256; never raises. Returns (ok, hex, note)
    """
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1024 * 1024), b""):
                h.update(b)
        return (True, h.hexdigest(), "OK")
    except Exception as e:
        return (False, "", "sha256_failed err=" + e.__class__.__name__)


def safe_case_id(raw: str, idx: int) -> str:
    s = (raw or "").strip()
    if not s:
        return "idx_" + str(idx).zfill(6)
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    s = s.strip("._-")
    if not s:
        return "idx_" + str(idx).zfill(6)
    if len(s) > 80:
        s = s[:80]
    return s


# -------------------------
# Dataset streaming
# -------------------------
def read_jsonl_stream(path):
    """
    Yields (line_index, obj, parse_ok, note); never raises.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    yield (i, None, False, "empty_line")
                    continue
                try:
                    obj = json.loads(line)
                    yield (i, obj, True, "OK")
                except Exception as e:
                    yield (i, None, False, "json_parse_failed err=" + e.__class__.__name__)
    except Exception as e:
        yield (-1, None, False, "open_failed err=" + e.__class__.__name__)


def extract_case_payload(obj, idx):
    """
    Returns (ok, case_id, payload_obj, note)
    payload_obj will be written to case_input.json.
    """
    try:
        if not isinstance(obj, dict):
            return (False, safe_case_id("", idx), None, "not_object")

        cid = ""
        for k in ["case_id", "id", "name"]:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                cid = v.strip()
                break
        case_id = safe_case_id(cid, idx)

        il_obj = None
        for k in ["il", "il_obj", "il_json", "il_body"]:
            v = obj.get(k)
            if isinstance(v, dict):
                il_obj = v
                break

        if il_obj is None:
            p = obj.get("il_path")
            if not p and isinstance(obj.get("payload"), dict):
                p = obj.get("payload").get("il_path")
            if isinstance(p, str) and p.strip():
                p2 = p.strip()
                if os.path.isfile(p2):
                    try:
                        if os.path.getsize(p2) <= 1024 * 1024:
                            with open(p2, "r", encoding="utf-8") as f:
                                il_obj = json.load(f)
                    except Exception:
                        il_obj = None

        if il_obj is None:
            # mild heuristic: case itself might be IL-like
            if "steps" in obj and isinstance(obj.get("steps"), list):
                il_obj = obj
            elif "ops" in obj and isinstance(obj.get("ops"), list):
                il_obj = obj
            elif "instructions" in obj and isinstance(obj.get("instructions"), list):
                il_obj = obj

        if il_obj is None:
            return (False, case_id, None, "il_not_found_in_case")

        payload = {
            "schema_version": "s22-08-case-input-v1",
            "case_id": case_id,
            "il": il_obj,
        }
        return (True, case_id, payload, "OK")
    except Exception as e:
        return (False, safe_case_id("", idx), None, "extract_failed err=" + e.__class__.__name__)


# -------------------------
# Entry interface discovery (light)
# -------------------------
def discover_entry_interface(timeout_sec=2):
    """
    Runs: python3 scripts/il_entry.py --help
    Never raises. Returns dict iface:
      {
        "help_ok": bool,
        "has_in": bool, "has_out": bool,
        "has_input": bool, "has_output": bool,
        "positional_hint": bool,
        "has_execute": bool, "has_exec": bool,
        "raw_tail": str
      }
    """
    iface = {
        "help_ok": False,
        "has_in": False, "has_out": False,
        "has_input": False, "has_output": False,
        "positional_hint": False,
        "has_execute": False, "has_exec": False,
        "raw_tail": "",
        "note": "OK",
    }
    # get absolute path of entry script relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # if this script is in scripts/, il_entry.py should be in same dir
    entry_script = os.path.join(script_dir, "il_entry.py")
    if not os.path.exists(entry_script):
        # fallback to repo root based find
        entry_script = "scripts/il_entry.py"

    try:
        p = subprocess.run(
            ["python3", entry_script, "--help"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        txt = (p.stdout or "") + "\n" + (p.stderr or "")
        tail = txt[-20000:] if len(txt) > 20000 else txt
        iface["raw_tail"] = tail
        low = tail.lower()

        iface["has_in"] = ("--in" in low)
        iface["has_out"] = ("--out" in low)
        iface["has_input"] = ("--input" in low)
        iface["has_output"] = ("--output" in low)
        iface["has_execute"] = ("--execute" in low)
        iface["has_exec"] = ("--exec" in low)

        usage_lines = []
        for line in tail.splitlines():
            if line.lower().startswith("usage:"):
                usage_lines.append(line.strip())
        usage = " ".join(usage_lines).lower()
        if "il_entry.py" in usage:
            if (not iface["has_in"]) and (not iface["has_input"]):
                if re.search(r"\bil_entry\.py\b.*\b(in|input|file)\b", usage):
                    iface["positional_hint"] = True
        iface["help_ok"] = True
        return iface
    except subprocess.TimeoutExpired:
        iface["note"] = "help_timeout"
        return iface
    except Exception as e:
        iface["note"] = "help_failed err=" + e.__class__.__name__
        return iface


# -------------------------
# Build entry attempts (3 strategies; try max 2)
# -------------------------
def build_entry_attempts(case_dir, payload_obj, mode, iface, max_attempts):
    try:
        os.makedirs(case_dir, exist_ok=True)
    except Exception as e:
        return (False, [], "mkdir_case_dir_failed err=" + e.__class__.__name__)

    case_input_path = os.path.join(case_dir, "case_input.json")
    ok, note = json_dump_atomic(case_input_path, payload_obj)
    if not ok:
        return (False, [], "case_input_write_failed " + note)

    exec_flag_variants = [[]]
    if mode == "validate-exec":
        ef = []
        if iface.get("help_ok"):
            if iface.get("has_execute"): ef.append(["--execute"])
            if iface.get("has_exec"): ef.append(["--exec"])
        if not ef:
            ef.append(["--execute"])
        exec_flag_variants = ef

    entry_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "il_entry.py")
    if not os.path.exists(entry_script): entry_script = "scripts/il_entry.py"

    base = ["python3", entry_script]
    strat_cmds = []

    for ef in exec_flag_variants:
        strat_cmds.append(("positional", base + [case_input_path, case_dir] + ef))

    if (not iface.get("help_ok")) or (iface.get("has_in") and iface.get("has_out")):
        for ef in exec_flag_variants:
            strat_cmds.append(("in_out", base + ["--in", case_input_path, "--out", case_dir] + ef))

    if (not iface.get("help_ok")) or (iface.get("has_input") and iface.get("has_output")):
        for ef in exec_flag_variants:
            strat_cmds.append(("input_output", base + ["--input", case_input_path, "--output", case_dir] + ef))

    prioritized = []
    if iface.get("help_ok"):
        if iface.get("has_in") and iface.get("has_out"):
            for name, cmd in strat_cmds:
                if name == "in_out": prioritized.append(cmd)
        if iface.get("has_input") and iface.get("has_output"):
            for name, cmd in strat_cmds:
                if name == "input_output": prioritized.append(cmd)
        for name, cmd in strat_cmds:
            if name == "positional": prioritized.append(cmd)
    else:
        for want in ["positional", "in_out", "input_output"]:
            for name, cmd in strat_cmds:
                if name == want: prioritized.append(cmd)

    dedup = []
    seen = set()
    for cmd in prioritized:
        key = " ".join(cmd)
        if key not in seen:
            seen.add(key)
            dedup.append(cmd)

    ma = 2
    try: ma = int(max_attempts)
    except: ma = 2
    if ma < 1: ma = 1
    if ma > 2: ma = 2

    attempts = dedup[:ma]
    if not attempts:
        attempts = [base + [case_input_path, case_dir]]

    return (True, attempts, "OK")


# -------------------------
# Run entry
# -------------------------
def run_entry_attempts(attempts, case_dir, stdout_path, stderr_path, timeout_sec):
    MAX_BYTES = 1024 * 1024
    def _append_text(path, s):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f: f.write(s)
        except: pass
    def _append_bytes(path, b):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "ab") as f:
                if len(b) > MAX_BYTES:
                    f.write(b[:MAX_BYTES])
                    f.write(b"\n[TRUNCATED]\n")
                else:
                    f.write(b)
                if not b.endswith(b"\n"): f.write(b"\n")
        except: pass

    used_cmd = []
    for ai, cmd in enumerate(attempts):
        used_cmd = cmd
        hdr = "== attempt=" + str(ai) + " cmd=" + " ".join(cmd) + " ==\n"
        _append_text(stdout_path, hdr)
        _append_text(stderr_path, hdr)
        try:
            p = subprocess.run(cmd, capture_output=True, text=False, timeout=timeout_sec, cwd=case_dir)
            outb = p.stdout or b""; errb = p.stderr or b""
            _append_bytes(stdout_path, outb); _append_bytes(stderr_path, errb)
            tail = (errb[-4096:] if len(errb) > 4096 else errb).decode("utf-8", errors="replace").lower()
            if ("unrecognized arguments" in tail) or ("error: unrecognized" in tail) or ("usage:" in tail and "il_entry.py" in tail):
                continue
            return (True, "OK", used_cmd)
        except subprocess.TimeoutExpired:
            _append_text(stderr_path, "ERROR: timeout_expired sec=" + str(timeout_sec) + "\n")
            return (False, "timeout_expired", used_cmd)
        except Exception as e:
            _append_text(stderr_path, "ERROR: subprocess_failed err=" + e.__class__.__name__ + "\n")
            return (False, "subprocess_failed err=" + e.__class__.__name__, used_cmd)
    return (False, "all_attempts_bad_args", used_cmd)


def parse_entry_status(stdout_path, stderr_path):
    def _tail(path, n=65536):
        try:
            with open(path, "rb") as f:
                try:
                    f.seek(0, os.SEEK_END); size = f.tell()
                    f.seek(max(0, size - n), os.SEEK_SET)
                except: pass
                return f.read().decode("utf-8", errors="replace")
        except: return ""
    out = _tail(stdout_path); err = _tail(stderr_path)
    lines = (out + "\n" + err).splitlines()
    last = ""
    for line in lines:
        line = line.strip()
        if line.startswith("OK:") or line.startswith("ERROR:") or line.startswith("SKIP:"):
            last = line
    if not last: return ("ERROR", "UNKNOWN", "no_status_marker")
    if last.startswith("OK:"): return ("OK", "NONE", "marker_ok")
    if last.startswith("SKIP:"): return ("SKIP", "ENTRY_ERROR", "marker_skip")
    return ("ERROR", "ENTRY_ERROR", "marker_error")


# -------------------------
# Rebuild & Audit
# -------------------------
def rebuild_summary(out_dir, cases_glob, timebox_sec, max_files):
    t0 = time.monotonic()
    meta = {"scanned": 0, "timebox_hit": False, "clamped": False}
    samples = {"status_errorcode_pairs": [], "parse_fail_paths": []}
    summary = {"schema_version": "s22-08-summary-v1", "total": 0, "ok": 0, "error": 0, "skip": 0, "breakdown_by_error_code": {}}
    try:
        pattern = os.path.join(out_dir, cases_glob)
        paths = sorted(_glob.glob(pattern))
    except Exception as e:
        return (False, summary, "glob_failed err=" + e.__class__.__name__, meta, samples)

    mf = int(max_files) if max_files else 5000
    if len(paths) > mf:
        paths = paths[:mf]; meta["clamped"] = True

    bd = {}
    SAMPLE_MAX = 200
    for pth in paths:
        if (time.monotonic() - t0) > float(timebox_sec):
            meta["timebox_hit"] = True; break
        try:
            with open(pth, "r", encoding="utf-8") as f:
                obj = json.load(f)
            
            ok_v, note_v, norm = validate_result_schema(obj)
            status = norm["status"]
            error_code = norm["error_code"]
            
            if not ok_v:
                # schema error
                summary["total"] += 1; summary["error"] += 1
                bd["RESULT_SCHEMA"] = int(bd.get("RESULT_SCHEMA", 0)) + 1
            else:
                summary["total"] += 1
                if status == "OK": summary["ok"] += 1
                elif status == "SKIP": summary["skip"] += 1
                else: summary["error"] += 1
                if error_code != "NONE":
                    bd[error_code] = int(bd.get(error_code, 0)) + 1
            
            if len(samples["status_errorcode_pairs"]) < SAMPLE_MAX:
                samples["status_errorcode_pairs"].append({"case_id": norm.get("case_id",""), "status": status, "error_code": error_code})
        except Exception:
            summary["total"] += 1; summary["error"] += 1
            bd["RESULT_PARSE"] = int(bd.get("RESULT_PARSE", 0)) + 1
            if len(samples["parse_fail_paths"]) < 50: samples["parse_fail_paths"].append(pth)
        meta["scanned"] += 1
    summary["breakdown_by_error_code"] = bd
    return (True, summary, "OK", meta, samples)


def audit_from_rebuild(out_dir, cases_glob, summary_obj, meta, samples):
    audit = {
        "schema_version": "s22-08-audit-v1", "out_dir": out_dir, "cases_glob": cases_glob,
        "scanned": int(meta.get("scanned", 0)), "timebox_hit": bool(meta.get("timebox_hit", False)),
        "clamped": bool(meta.get("clamped", False)), "counts_from_cases": summary_obj,
        "checks": {}, "fingerprints": {"result_files_sha256_sample": []},
        "started_at_utc": now_utc_z(), "ended_at_utc": now_utc_z(),
    }
    total = int(summary_obj.get("total", 0))
    okc = int(summary_obj.get("ok", 0)); errc = int(summary_obj.get("error", 0)); skipc = int(summary_obj.get("skip", 0))
    bd = summary_obj.get("breakdown_by_error_code") or {}
    a_ok = (total == (okc + errc + skipc))
    audit["checks"]["sum_status_equals_total"] = {"ok": bool(a_ok), "note": "OK" if a_ok else "mismatch"}
    bsum = sum(int(v) for v in bd.values() if str(v).isdigit())
    b_ok = (bsum <= total)
    audit["checks"]["breakdown_le_total"] = {"ok": bool(b_ok), "note": "OK" if b_ok else "breakdown_sum_gt_total"}
    c_ok = True; bad_examples = []
    pairs = samples.get("status_errorcode_pairs") or []
    for it in pairs:
        st = str(it.get("status", "")).strip(); ec = str(it.get("error_code", "")).strip()
        if (st == "OK" and ec != "NONE") or (st != "OK" and ec == "NONE"):
            c_ok = False
            if len(bad_examples) < 10: bad_examples.append(it)
    audit["checks"]["errorcode_none_only_ok"] = {"ok": bool(c_ok), "note": "OK" if c_ok else "found_mismatch", "examples": bad_examples}
    overall = bool(a_ok and b_ok and c_ok)
    return (overall, audit, "OK" if overall else "audit_failed")


def validate_result_schema(obj):
    norm = {"case_id": "", "status": "ERROR", "error_code": "RESULT_SCHEMA", "mode": ""}
    try:
        if not isinstance(obj, dict):
            return (False, "not_object", norm)

        sv = str(obj.get("schema_version", "")).strip()
        if sv != "s22-08-result-v1":
            # still extract best-effort
            cid = obj.get("case_id")
            if isinstance(cid, str):
                norm["case_id"] = cid.strip()
            st = obj.get("status")
            if isinstance(st, str) and st.strip() in ["OK", "ERROR", "SKIP"]:
                norm["status"] = st.strip()
            md = obj.get("mode")
            if isinstance(md, str):
                norm["mode"] = md.strip()
            return (False, "schema_version_mismatch got=" + sv, norm)

        cid = obj.get("case_id")
        if isinstance(cid, str):
            norm["case_id"] = cid.strip()

        st = obj.get("status")
        if isinstance(st, str) and st.strip() in ["OK", "ERROR", "SKIP"]:
            norm["status"] = st.strip()
        else:
            return (False, "missing_or_invalid_status", norm)

        ec = obj.get("error_code")
        if isinstance(ec, str) and ec.strip():
            norm["error_code"] = ec.strip()
        else:
            return (False, "missing_error_code", norm)

        md = obj.get("mode")
        if isinstance(md, str):
            norm["mode"] = md.strip()

        ds = obj.get("dataset")
        if not isinstance(ds, dict):
            return (False, "missing_dataset", norm)
        if not isinstance(ds.get("path"), str) or not str(ds.get("path")).strip():
            return (False, "missing_dataset_path", norm)
        try:
            _ = int(ds.get("line_index"))
        except Exception:
            return (False, "missing_or_invalid_line_index", norm)

        en = obj.get("entry")
        if not isinstance(en, dict):
            return (False, "missing_entry", norm)
        if not isinstance(en.get("cmd"), list):
            return (False, "missing_entry_cmd", norm)

        tm = obj.get("timing")
        if not isinstance(tm, dict):
            return (False, "missing_timing", norm)
        if not isinstance(tm.get("started_at_utc"), str) or not str(tm.get("started_at_utc")).strip():
            return (False, "missing_started_at_utc", norm)
        if not isinstance(tm.get("ended_at_utc"), str) or not str(tm.get("ended_at_utc")).strip():
            return (False, "missing_ended_at_utc", norm)

        return (True, "OK", norm)
    except Exception as e:
        return (False, "validator_failed err=" + e.__class__.__name__, norm)


def validate_audit_schema(obj):
    """
    Validate minimal schema for s22-08-audit-v1.
    Never raises. Returns (ok, note).
    """
    try:
        if not isinstance(obj, dict):
            return (False, "not_object")

        sv = str(obj.get("schema_version", "")).strip()
        if sv != "s22-08-audit-v1":
            return (False, "schema_version_mismatch got=" + sv)

        # required strings
        if not isinstance(obj.get("out_dir"), str) or not str(obj.get("out_dir")).strip():
            return (False, "missing_out_dir")
        if not isinstance(obj.get("cases_glob"), str) or not str(obj.get("cases_glob")).strip():
            return (False, "missing_cases_glob")

        # required scalars
        try:
            _ = int(obj.get("scanned"))
        except Exception:
            return (False, "missing_or_invalid_scanned")

        # bool-like (accept bool or 0/1)
        for k in ["timebox_hit", "clamped"]:
            v = obj.get(k)
            if isinstance(v, bool):
                pass
            elif isinstance(v, int) and v in [0, 1]:
                pass
            else:
                return (False, "missing_or_invalid_" + k)

        cfc = obj.get("counts_from_cases")
        if not isinstance(cfc, dict):
            return (False, "missing_counts_from_cases")

        for k in ["total", "ok", "error", "skip"]:
            try:
                _ = int(cfc.get(k))
            except Exception:
                return (False, "missing_or_invalid_counts_" + k)

        bd = cfc.get("breakdown_by_error_code")
        if not isinstance(bd, dict):
            return (False, "missing_breakdown_by_error_code")

        checks = obj.get("checks")
        if not isinstance(checks, dict):
            return (False, "missing_checks")

        for k in ["started_at_utc", "ended_at_utc"]:
            if not isinstance(obj.get(k), str) or not str(obj.get(k)).strip():
                return (False, "missing_" + k)

        return (True, "OK")

    except Exception as e:
        return (False, "validator_failed err=" + e.__class__.__name__)


def make_fallback_audit(out_dir, cases_glob, note, meta):
    """
    Minimal audit object that is always schema-valid.
    """
    return {
        "schema_version": "s22-08-audit-v1",
        "out_dir": out_dir,
        "cases_glob": cases_glob,
        "scanned": int(meta.get("scanned", 0)),
        "timebox_hit": bool(meta.get("timebox_hit", False)),
        "clamped": bool(meta.get("clamped", False)),
        "counts_from_cases": {
            "total": 0, "ok": 0, "error": 0, "skip": 0,
            "breakdown_by_error_code": {"AUDIT_SCHEMA": 1}
        },
        "checks": {
            "audit_schema_self_check": {"ok": False, "note": note}
        },
        "fingerprints": {"result_files_sha256_sample": []},
        "started_at_utc": now_utc_z(),
        "ended_at_utc": now_utc_z()
    }


# -------------------------
# Main
# -------------------------
def main():
    STOP = 0
    p = SafeArgumentParser(add_help=True)
    p.add_argument("--dataset", default="")
    p.add_argument("--out", default="")
    p.add_argument("--mode", default="validate-only")
    p.add_argument("--offset", default="0")
    p.add_argument("--limit", default="5")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--timebox-sec", default="20")
    p.add_argument("--case-timeout-sec", default="10")
    p.add_argument("--max-attempts", default="2")
    p.add_argument("--rebuild-summary", action="store_true")
    p.add_argument("--cases-glob", default="cases/*/result.json")
    p.add_argument("--rebuild-timebox-sec", default="10")
    p.add_argument("--rebuild-max-files", default="5000")
    p.add_argument("--audit", action="store_true")
    p.add_argument("--audit-fingerprint", action="store_true")
    p.add_argument("--audit-fingerprint-max", default="50")
    p.add_argument("--audit-fingerprint-timebox-sec", default="5")

    args = p.parse_args()
    if getattr(p, "_safe_error", ""):
        print("ERROR: argparse " + p._safe_error); STOP = 1

    dataset = (args.dataset or "").strip()
    out_dir = (args.out or "").strip()
    mode = (args.mode or "").strip()

    if STOP == 0:
        if not out_dir: print("ERROR: out_required"); STOP = 1
        elif not os.path.exists(out_dir): os.makedirs(out_dir, exist_ok=True)

    # Rebuild branch
    if STOP == 0 and args.rebuild_summary:
        ok_i, rtb, _ = _to_int(args.rebuild_timebox_sec, "rebuild-timebox-sec", 10)
        ok_i, rmax, _ = _to_int(args.rebuild_max_files, "rebuild-max-files", 5000)
        ok_rb, summary_obj, note_rb, meta, samples = rebuild_summary(out_dir, args.cases_glob, rtb, rmax)
        json_dump_atomic(os.path.join(out_dir, "summary.json"), summary_obj)
        ov_ok, audit_obj, a_note = audit_from_rebuild(out_dir, args.cases_glob, summary_obj, meta, samples)
        
        audit_path = os.path.join(out_dir, "audit.json")
        json_dump_atomic(audit_path, audit_obj)

        # self-validate audit.json (stopless)
        try:
            with open(audit_path, "r", encoding="utf-8") as f:
                tmp = json.load(f)
            ok_as, note_as = validate_audit_schema(tmp)
            if ok_as:
                print("OK: audit_schema_valid")
            else:
                print("ERROR: audit_schema_invalid note=" + note_as)
                fb = make_fallback_audit(out_dir, (args.cases_glob or "cases/*/result.json"), note_as, meta)
                json_dump_atomic(audit_path, fb)
        except Exception as e:
            print("ERROR: audit_readback_failed err=" + e.__class__.__name__)
            fb = make_fallback_audit(out_dir, (args.cases_glob or "cases/*/result.json"), "readback_failed", meta)
            json_dump_atomic(audit_path, fb)

        print("OK: rebuild_summary total="+str(summary_obj["total"])+" scanned="+str(meta["scanned"])+" audit="+("PASS" if ov_ok else "FAIL"))
        print("OK: done stop=0"); return

    # Runner branch
    if STOP == 0:
        if not dataset: print("ERROR: dataset_required"); STOP = 1
        elif not os.path.isfile(dataset): print("ERROR: dataset_missing"); STOP = 1
        if mode not in ["validate-only", "validate-exec"]: print("ERROR: invalid_mode"); STOP = 1

    if STOP == 0:
        iface = discover_entry_interface()
        ds_ok, ds_sha, ds_note = sha256_file(dataset)
        if not ds_ok: print("ERROR: dataset_sha_failed " + ds_note); STOP = 1

    if STOP == 0:
        ok_off, offset, _ = _to_int(args.offset, "offset", 0)
        ok_lim, limit, _ = _to_int(args.limit, "limit", 5)
        ok_tb, timebox_sec, _ = _to_int(args.timebox_sec, "timebox-sec", 20)
        ok_ct, case_timeout, _ = _to_int(args.case_timeout_sec, "case-timeout-sec", 10)

        run_path = os.path.join(out_dir, "run.json")
        summary_path = os.path.join(out_dir, "summary.json")
        run_obj = {"schema_version": "s22-08-run-v1", "dataset_path": dataset, "dataset_sha256": ds_sha, "segments": []}
        summary_obj = {"schema_version": "s22-08-summary-v1", "total": 0, "ok": 0, "error": 0, "skip": 0, "breakdown_by_error_code": {}}
        # load existing if resume
        try:
            if os.path.isfile(run_path):
                with open(run_path, "r") as f: run_obj.update(json.load(f))
            if os.path.isfile(summary_path):
                with open(summary_path, "r") as f: summary_obj.update(json.load(f))
        except: pass

        t0 = time.monotonic(); processed = 0
        print("OK: phase=start out="+out_dir+" dataset="+dataset)
        for i, obj, p_ok, p_note in read_jsonl_stream(dataset):
            if i < offset: continue
            if processed >= limit or (time.monotonic() - t0) > timebox_sec: break
            
            case_started = now_utc_z()
            cid_pre = safe_case_id("", i)
            case_dir = os.path.join(out_dir, "cases", cid_pre)
            os.makedirs(case_dir, exist_ok=True)
            res_path = os.path.join(case_dir, "result.json")
            if args.resume and os.path.isfile(res_path):
                print("SKIP: idx="+str(i)+" reason=already_done"); processed += 1; continue

            used_c = []
            if not p_ok: status = "ERROR"; ec = "DATASET_PARSE"; note = p_note; case_id = cid_pre
            else:
                ok_p, case_id, payload, note_p = extract_case_payload(obj, i)
                if not ok_p: status = "ERROR"; ec = "DATASET_SCHEMA"; note = note_p
                else:
                    if case_id != cid_pre:
                        case_dir = os.path.join(out_dir, "cases", case_id)
                        os.makedirs(case_dir, exist_ok=True)
                        res_path = os.path.join(case_dir, "result.json")
                    ok_a, atts, note_a = build_entry_attempts(case_dir, payload, mode, iface, args.max_attempts)
                    if not ok_a: status = "ERROR"; ec = "RESULT_WRITE"; note = note_a
                    else:
                        out_p = os.path.join(case_dir, "entry_stdout.txt")
                        err_p = os.path.join(case_dir, "entry_stderr.txt")
                        t_c0 = time.monotonic()
                        ok_r, note_r, used_c = run_entry_attempts(atts, case_dir, out_p, err_p, case_timeout)
                        dur = int((time.monotonic() - t_c0)*1000)
                        if not ok_r:
                            status = "ERROR"; ec = "ENTRY_TIMEOUT" if note_r=="timeout_expired" else ("ENTRY_BAD_ARGS" if note_r=="all_attempts_bad_args" else "ENTRY_CRASH")
                            note = note_r
                        else:
                            status, ec, note = parse_entry_status(out_p, err_p)
            
            res = {
                "schema_version": "s22-08-result-v1", "case_id": case_id, "status": status, "error_code": ec,
                "mode": mode, "dataset": {"path": dataset, "line_index": i},
                "entry": {"cmd": used_c if isinstance(used_c, list) else []},
                "timing": {"started_at_utc": case_started, "ended_at_utc": now_utc_z(), "duration_ms": int((time.monotonic()-t0)*1000)},
                "notes": note
            }
            json_dump_atomic(res_path, res)
            print(status + ": case="+case_id+" error="+ec)
            summary_obj["total"] += 1
            if status == "OK": summary_obj["ok"] += 1
            elif status == "SKIP": summary_obj["skip"] += 1
            else:
                summary_obj["error"] += 1
                bd = summary_obj.get("breakdown_by_error_code") or {}
                bd[ec] = bd.get(ec, 0) + 1; summary_obj["breakdown_by_error_code"] = bd
            processed += 1

        run_obj["segments"].append({"mode":mode, "offset":offset, "limit":limit, "started":now_utc_z()})
        json_dump_atomic(run_path, run_obj)
        json_dump_atomic(summary_path, summary_obj)
        
        # audit always - best effort on current summary
        try:
            ov_ok, audit_obj, a_note = audit_from_rebuild(out_dir, args.cases_glob, summary_obj, {"scanned": processed}, {})
            audit_path = os.path.join(out_dir, "audit.json")
            json_dump_atomic(audit_path, audit_obj)

            # self-validate audit.json (stopless)
            try:
                with open(audit_path, "r", encoding="utf-8") as f:
                    tmp = json.load(f)
                ok_as, note_as = validate_audit_schema(tmp)
                if ok_as:
                    print("OK: audit_schema_valid")
                else:
                    print("ERROR: audit_schema_invalid note=" + note_as)
                    fb = make_fallback_audit(out_dir, (args.cases_glob or "cases/*/result.json"), note_as, {"scanned": processed})
                    json_dump_atomic(audit_path, fb)
            except Exception as e:
                print("ERROR: audit_readback_failed err=" + e.__class__.__name__)
                fb = make_fallback_audit(out_dir, (args.cases_glob or "cases/*/result.json"), "readback_failed", {"scanned": processed})
                json_dump_atomic(audit_path, fb)
        except: pass

        # SHA256SUMS best-effort
        sums_path = os.path.join(out_dir, "SHA256SUMS.txt")
        lines = []
        for rel in ["run.json", "summary.json", "audit.json"]:
            p2 = os.path.join(out_dir, rel)
            okh, hx, _ = sha256_file(p2)
            if okh:
                lines.append(hx + "  " + rel)
        try:
            with open(sums_path, "w", encoding="utf-8") as f:
                for ln in lines:
                    f.write(ln + "\n")
        except Exception:
            pass

        print("OK: summary total="+str(summary_obj["total"])+" ok="+str(summary_obj["ok"]))

    print("OK: done stop="+str(STOP))

if __name__ == "__main__":
    try: main()
    except Exception as e: print("ERROR: crash err="+e.__class__.__name__); print("OK: done stop=1")
