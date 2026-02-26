#!/usr/bin/env python3
# Stopless: no sys.exit / no SystemExit. Returns 0 always.
import datetime
import json
import os
import re
import subprocess


def out(msg):
    try:
        print(msg)
    except Exception:
        pass


def run(cmd):
    try:
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return (cp.stdout or "", cp.stderr or "", cp.returncode)
    except Exception as exc:
        return ("", str(exc), 999)


def gh_api(endpoint):
    headers = ["-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28"]
    return run(["gh", "api"] + headers + [endpoint])


def repo_name():
    so, _, _ = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    return (so or "").strip()


def normalize_contexts(items):
    xs = []
    for raw in items or []:
        if isinstance(raw, str):
            v = raw.strip()
            if v:
                xs.append(v)
        elif isinstance(raw, dict):
            v = str(raw.get("context") or "").strip()
            if v:
                xs.append(v)
    return sorted(set(xs))


def read_doc_sot(doc_path):
    try:
        text = open(doc_path, "r", encoding="utf-8").read()
    except Exception:
        return None
    m = re.search(r"<!--\s*required_checks_sot:v1(.*?)-->", text, flags=re.S)
    if not m:
        return None
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return normalize_contexts(lines)


def read_ruleset_sot(json_path):
    try:
        obj = json.loads(open(json_path, "r", encoding="utf-8").read())
    except Exception:
        return None
    return normalize_contexts(obj.get("required_status_checks"))


def write_doc_sot(doc_path, contexts):
    clean = normalize_contexts(contexts)
    block = [
        "<!-- required_checks_sot:v1",
        "# auto-managed. run: bash ops/required_checks_sot.sh write-sot",
        "# NOTE: empty/missing live required checks => ERROR (fail-closed)",
    ]
    block.extend(clean)
    block.append("-->")
    block_text = "\n".join(block) + "\n"
    try:
        text = open(doc_path, "r", encoding="utf-8").read()
    except Exception:
        return False
    if re.search(r"<!--\s*required_checks_sot:v1.*?-->", text, flags=re.S):
        updated = re.sub(r"<!--\s*required_checks_sot:v1.*?-->", block_text.rstrip("\n"), text, flags=re.S)
    else:
        updated = text + "\n" + block_text
    try:
        open(doc_path, "w", encoding="utf-8").write(updated)
        return True
    except Exception:
        return False


def write_ruleset_sot(json_path, contexts, source):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = {}
    try:
        base = json.loads(open(json_path, "r", encoding="utf-8").read())
    except Exception:
        base = {}
    try:
        if not isinstance(base, dict):
            base = {}
        base["schema_version"] = int(base.get("schema_version", 1) or 1)
        base["updated_utc"] = now
        src = base.get("source")
        if not isinstance(src, dict):
            src = {}
        src["observed_by"] = source
        base["source"] = src
        base["required_status_checks"] = normalize_contexts(contexts)
        open(json_path, "w", encoding="utf-8").write(json.dumps(base, ensure_ascii=True, indent=2) + "\n")
        return True
    except Exception:
        return False


def fetch_live_from_branch_protection(repo, branch):
    if not repo:
        out("ERROR: repo name unavailable")
        return None, "unavailable"
    endpoint = f"repos/{repo}/branches/{branch}/protection/required_status_checks/contexts"
    so, se, rc = gh_api(endpoint)
    payload = None
    try:
        payload = json.loads(so) if (so or "").strip() else None
    except Exception:
        payload = None
    if isinstance(payload, list):
        contexts = normalize_contexts(payload)
        if not contexts:
            out("ERROR: required checks empty [fail-closed]")
            return None, "unavailable"
        return contexts, "branch_protection"
    msg = ""
    status = ""
    if isinstance(payload, dict):
        msg = str(payload.get("message") or "")
        status = str(payload.get("status") or "")
    se1 = ((se or "").strip().splitlines() or [""])[0]
    reason = f"status={status or 'NA'} rc={rc}"
    if msg:
        reason += f" msg={msg}"
    elif se1:
        reason += f" stderr={se1}"
    out(f"WARN: branch protection contexts unavailable ({reason})")
    return None, "unavailable"


def resolve_live(repo, branch, ruleset_sot_path):
    contexts, source = fetch_live_from_branch_protection(repo, branch)
    if contexts:
        return contexts, source
    fallback = read_ruleset_sot(ruleset_sot_path)
    if fallback:
        out(f"WARN: using ruleset SOT fallback n={len(fallback)}")
        return fallback, "ruleset_sot_fallback"
    return None, "unavailable"


def format_diff(expected, actual):
    missing = sorted(list(set(expected) - set(actual)))
    extra = sorted(list(set(actual) - set(expected)))
    return f"missing={missing if missing else 'NONE'} extra={extra if extra else 'NONE'}"


def main():
    mode = (os.environ.get("MODE") or "check").strip()
    repo = repo_name()
    branch = (os.environ.get("BRANCH") or "main").strip()
    doc_path = (os.environ.get("DOC") or "docs/ops/CI_REQUIRED_CHECKS.md").strip()
    ruleset_sot_path = (os.environ.get("RULESET_SOT") or "ops/ruleset_required_status_checks.json").strip()

    live, source = resolve_live(repo, branch, ruleset_sot_path)
    doc_sot = read_doc_sot(doc_path)
    ruleset_sot = read_ruleset_sot(ruleset_sot_path)

    if mode == "dump-live":
        if live:
            out(f"OK: live source={source} n={len(live)}")
            for item in live:
                out(item)
        else:
            out("ERROR: live checks unavailable [fail-closed]")
        return

    if mode == "write-sot":
        if not live:
            out("ERROR: write-sot blocked (live checks unavailable)")
            return
        ok_doc = write_doc_sot(doc_path, live)
        ok_ruleset = write_ruleset_sot(ruleset_sot_path, live, source)
        if ok_doc and ok_ruleset:
            out(f"OK: write-sot updated source={source} n={len(live)}")
        else:
            out(f"ERROR: write-sot failed doc_ok={ok_doc} ruleset_ok={ok_ruleset}")
        return

    if not live:
        out("ERROR: live checks unavailable [fail-closed]")
        return
    if doc_sot is None:
        out("ERROR: docs SOT block missing")
        return
    if ruleset_sot is None:
        out("ERROR: ruleset SOT file missing/invalid")
        return

    doc_diff = format_diff(live, doc_sot)
    ruleset_diff = format_diff(live, ruleset_sot)
    doc_match = (set(live) == set(doc_sot))
    ruleset_match = (set(live) == set(ruleset_sot))

    if doc_match and ruleset_match:
        out(f"OK: required_checks_sot matched source={source} n={len(live)}")
    else:
        if not doc_match:
            out(f"ERROR: docs_required_checks_sot drift {doc_diff}")
        if not ruleset_match:
            out(f"ERROR: ruleset_required_checks_sot drift {ruleset_diff}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        out(f"ERROR: exception {exc}")
