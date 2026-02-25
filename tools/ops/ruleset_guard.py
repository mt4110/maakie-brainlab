#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

def now_utc_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def p(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        # 最後の砦（print が落ちても黙って終える）
        pass

def run_cmd(args: List[str]) -> Tuple[bool, str, str]:
    try:
        cp = subprocess.run(args, capture_output=True, text=True)
        out = (cp.stdout or "").strip()
        err = (cp.stderr or "").strip()
        ok = (cp.returncode == 0)
        return ok, out, err
    except Exception as e:
        return False, "", f"{e}"

def git_origin_url() -> Optional[str]:
    ok, out, err = run_cmd(["git", "remote", "get-url", "origin"])
    if ok and out:
        return out.strip()
    if err:
        p(f"WARN: git remote get-url origin failed ({err})")
    return None

def parse_owner_repo_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    # git@github.com:owner/repo.git
    m = re.search(r"git@github\.com:([^/]+)/([^/]+?)(\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    # https://github.com/owner/repo.git
    m = re.search(r"https?://github\.com/([^/]+)/([^/]+?)(\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    # ssh://git@github.com/owner/repo.git
    m = re.search(r"ssh://git@github\.com/([^/]+)/([^/]+?)(\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    return None, None

def gh_available() -> bool:
    try:
        return shutil.which("gh") is not None
    except Exception:
        return False

def token_from_env() -> Optional[str]:
    for k in ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT"]:
        v = os.environ.get(k)
        if v:
            return v.strip()
    return None

def gh_api(path: str, method: str = "GET", payload_obj: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
    # path: "repos/{owner}/{repo}/rulesets"
    if gh_available():
        args = ["gh", "api", path, "--method", method]
        tmp = None
        if payload_obj is not None:
            try:
                tmp = pathlib.Path(".local") / "tmp_ruleset_guard_payload.json"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(payload_obj), encoding="utf-8")
                args += ["--input", str(tmp)]
            except Exception as e:
                p(f"ERROR: cannot write temp payload ({e})")
                return False, None
        ok, out, err = run_cmd(args)
        if tmp is not None:
            try:
                tmp.unlink()
            except Exception:
                pass
        if not ok:
            p(f"ERROR: gh api failed path={path} method={method} err={err}")
            return False, None
        try:
            return True, json.loads(out) if out else None
        except Exception as e:
            p(f"ERROR: cannot parse gh api json ({e})")
            return False, None

    tok = token_from_env()
    if not tok:
        p("ERROR: no gh cli, and no token in env (GITHUB_TOKEN/GH_TOKEN/GITHUB_PAT)")
        return False, None

    import urllib.request

    url = "https://api.github.com/" + path.lstrip("/")
    data = None
    if payload_obj is not None:
        try:
            data = json.dumps(payload_obj).encode("utf-8")
        except Exception as e:
            p(f"ERROR: cannot encode payload ({e})")
            return False, None

    req = urllib.request.Request(url=url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(body) if body else None
    except Exception as e:
        p(f"ERROR: curl-like request failed ({e})")
        return False, None

def list_rulesets(owner: str, repo: str) -> List[Dict[str, Any]]:
    ok, js = gh_api(f"repos/{owner}/{repo}/rulesets?per_page=100", "GET")
    if not ok or not isinstance(js, list):
        return []
    return js

def get_ruleset(owner: str, repo: str, ruleset_id: int) -> Optional[Dict[str, Any]]:
    ok, js = gh_api(f"repos/{owner}/{repo}/rulesets/{ruleset_id}", "GET")
    if ok and isinstance(js, dict):
        return js
    return None

def extract_required_status_checks(ruleset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return None
    for r in rules:
        if isinstance(r, dict) and r.get("type") == "required_status_checks":
            params = r.get("parameters") if isinstance(r.get("parameters"), dict) else {}
            items = params.get("required_status_checks", [])
            strict = params.get("strict_required_status_checks_policy", None)
            dne = params.get("do_not_enforce_on_create", None)
            # items: [{context, integration_id?}]
            norm_items = []
            if isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    ctx = it.get("context")
                    if isinstance(ctx, str) and ctx.strip():
                        norm_items.append({
                            "context": ctx.strip(),
                            "integration_id": it.get("integration_id", None)
                        })
            return {
                "required_status_checks": norm_items,
                "strict_required_status_checks_policy": strict,
                "do_not_enforce_on_create": dne,
            }
    return None

def select_rulesets(rulesets: List[Dict[str, Any]], ruleset_id: Optional[int], name_hint: Optional[str]) -> List[Dict[str, Any]]:
    if ruleset_id is not None:
        return [r for r in rulesets if r.get("id") == ruleset_id]
    if name_hint:
        nh = name_hint.lower()
        return [r for r in rulesets if isinstance(r.get("name"), str) and nh in r["name"].lower()]
    return rulesets

def discover_contexts(owner: str, repo: str, ref: str) -> List[str]:
    # union of check-runs names + commit status contexts
    contexts = set()

    ok1, js1 = gh_api(f"repos/{owner}/{repo}/commits/{ref}/check-runs?per_page=100", "GET")
    if ok1 and isinstance(js1, dict):
        cr = js1.get("check_runs")
        if isinstance(cr, list):
            for it in cr:
                nm = it.get("name") if isinstance(it, dict) else None
                if isinstance(nm, str) and nm.strip():
                    contexts.add(nm.strip())

    ok2, js2 = gh_api(f"repos/{owner}/{repo}/commits/{ref}/status?per_page=100", "GET")
    if ok2 and isinstance(js2, dict):
        sts = js2.get("statuses")
        if isinstance(sts, list):
            for it in sts:
                ctx = it.get("context") if isinstance(it, dict) else None
                if isinstance(ctx, str) and ctx.strip():
                    contexts.add(ctx.strip())

    return sorted(contexts)

def load_sot(path: str) -> Optional[Dict[str, Any]]:
    pth = pathlib.Path(path)
    if not pth.exists():
        return None
    try:
        return json.loads(pth.read_text(encoding="utf-8"))
    except Exception as e:
        p(f"ERROR: cannot read SOT json ({e}) path={path}")
        return None

def write_sot(path: str, owner: str, repo: str, ruleset_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    obj = {
        "schema_version": 1,
        "updated_utc": now_utc_iso(),
        "source": {
            "owner": owner,
            "repo": repo,
            "ruleset_id": ruleset_meta.get("id"),
            "ruleset_name": ruleset_meta.get("name"),
        },
        "required_status_checks": req.get("required_status_checks", []),
        "strict_required_status_checks_policy": req.get("strict_required_status_checks_policy", None),
        "do_not_enforce_on_create": req.get("do_not_enforce_on_create", None),
    }
    try:
        pth = pathlib.Path(path)
        pth.parent.mkdir(parents=True, exist_ok=True)
        pth.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        p(f"OK: wrote SOT {path}")
        return True
    except Exception as e:
        p(f"ERROR: cannot write SOT ({e}) path={path}")
        return False

def build_update_payload(ruleset_full: Dict[str, Any], new_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload = {}
    for k in ["name", "target", "enforcement", "conditions"]:
        if k in ruleset_full:
            payload[k] = ruleset_full.get(k)
    if "bypass_actors" in ruleset_full:
        payload["bypass_actors"] = ruleset_full.get("bypass_actors")
    payload["rules"] = new_rules
    return payload

def sync_required_checks(owner: str, repo: str, ruleset_id: int, sot: Dict[str, Any]) -> bool:
    apply_env = os.environ.get("APPLY", "")
    if apply_env != "1":
        p("SKIP: APPLY env not set (dry-run)")
        return False

    rs = get_ruleset(owner, repo, ruleset_id)
    if not rs:
        p("ERROR: cannot fetch ruleset for sync")
        return False

    rules = rs.get("rules")
    if not isinstance(rules, list):
        p("ERROR: ruleset has no rules list")
        return False

    sot_list = sot.get("required_status_checks", [])
    if not isinstance(sot_list, list):
        p("ERROR: SOT required_status_checks not a list")
        return False

    # replace required_status_checks rule
    updated = False
    new_rules = []
    for r in rules:
        if isinstance(r, dict) and r.get("type") == "required_status_checks":
            params = r.get("parameters") if isinstance(r.get("parameters"), dict) else {}
            params["required_status_checks"] = sot_list
            if "strict_required_status_checks_policy" in sot:
                params["strict_required_status_checks_policy"] = sot.get("strict_required_status_checks_policy")
            if "do_not_enforce_on_create" in sot:
                params["do_not_enforce_on_create"] = sot.get("do_not_enforce_on_create")
            new_rules.append({"type": "required_status_checks", "parameters": params})
            updated = True
        else:
            new_rules.append(r)

    if not updated:
        p("ERROR: required_status_checks rule not found in ruleset")
        return False

    payload = build_update_payload(rs, new_rules)
    ok, js = gh_api(f"repos/{owner}/{repo}/rulesets/{ruleset_id}", "PUT", payload_obj=payload)
    if ok:
        p("OK: sync done (ruleset updated)")
        return True
    p("ERROR: sync failed (api call)")
    return False

def help_text() -> str:
    return (
        "ruleset_guard.py commands:\n"
        "  list-rulesets [--ruleset-name NAME] [--ruleset-id ID]\n"
        "  discover --ref REF\n"
        "  audit [--ref REF] [--ruleset-name NAME|--ruleset-id ID] [--sot PATH]\n"
        "  write-sot --ruleset-id ID [--sot PATH]\n"
        "  sync --ruleset-id ID [--sot PATH]  (requires APPLY=1 env)\n"
    )

def main(argv: List[str]) -> None:
    cmd = "audit"
    if len(argv) >= 2 and not argv[1].startswith("-"):
        cmd = argv[1]

    ruleset_id = None
    ruleset_name = None
    ref = None
    sot_path = "ops/ruleset_required_status_checks.json"

    i = 2
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help", "help"):
            p(help_text())
            return
        if a == "--ruleset-id" and i + 1 < len(argv):
            try:
                ruleset_id = int(argv[i + 1])
            except Exception:
                p("ERROR: --ruleset-id must be int")
            i += 2
            continue
        if a == "--ruleset-name" and i + 1 < len(argv):
            ruleset_name = argv[i + 1]
            i += 2
            continue
        if a == "--ref" and i + 1 < len(argv):
            ref = argv[i + 1]
            i += 2
            continue
        if a == "--sot" and i + 1 < len(argv):
            sot_path = argv[i + 1]
            i += 2
            continue
        p(f"WARN: unknown arg {a}")
        i += 1

    url = git_origin_url()
    owner = None
    repo = None
    if url:
        owner, repo = parse_owner_repo_from_url(url)

    if not owner or not repo:
        # env fallback
        owner = os.environ.get("OWNER")
        repo = os.environ.get("REPO")

    if not owner or not repo:
        p("ERROR: cannot determine owner/repo (origin parse failed). Set OWNER/REPO env.")
        return

    p(f"OK: repo={owner}/{repo}")
    p(f"OK: time_utc={now_utc_iso()}")

    if cmd == "list-rulesets":
        rs = list_rulesets(owner, repo)
        if not rs:
            p("ERROR: no rulesets (or cannot fetch)")
            return
        for r in rs:
            rid = r.get("id")
            nm = r.get("name")
            enf = r.get("enforcement")
            tgt = r.get("target")
            p(f"OK: ruleset id={rid} name={nm} target={tgt} enforcement={enf}")
        return

    if cmd == "discover":
        if not ref:
            p("ERROR: discover requires --ref REF")
            return
        ctx = discover_contexts(owner, repo, ref)
        p(f"OK: discovered_contexts_count={len(ctx)} ref={ref}")
        for c in ctx:
            p(f"OK: ctx {c}")
        return

    # common: load rulesets + select + fetch full
    rs_list = list_rulesets(owner, repo)
    if not rs_list:
        p("ERROR: cannot fetch rulesets list")
        return

    selected = select_rulesets(rs_list, ruleset_id, ruleset_name)
    if not selected:
        p("ERROR: no rulesets matched selector")
        return

    if cmd == "write-sot":
        if ruleset_id is None:
            p("ERROR: write-sot requires --ruleset-id ID")
            return
        full = get_ruleset(owner, repo, ruleset_id)
        if not full:
            p("ERROR: cannot fetch ruleset for write-sot")
            return
        req = extract_required_status_checks(full)
        if not req:
            p("ERROR: ruleset has no required_status_checks rule")
            return
        write_sot(sot_path, owner, repo, {"id": ruleset_id, "name": full.get("name")}, req)
        return

    if cmd == "sync":
        if ruleset_id is None:
            p("ERROR: sync requires --ruleset-id ID")
            return
        sot = load_sot(sot_path)
        if not sot:
            p("ERROR: cannot load SOT (missing or invalid)")
            return
        sync_required_checks(owner, repo, ruleset_id, sot)
        return

    # audit default
    if not ref:
        ok, out, err = run_cmd(["git", "rev-parse", "HEAD"])
        ref = out.strip() if ok and out else "HEAD"
    p(f"OK: audit_ref={ref}")

    observed = discover_contexts(owner, repo, ref)
    p(f"OK: observed_contexts_count={len(observed)}")

    sot = load_sot(sot_path)
    if sot:
        sot_req = sot.get("required_status_checks", [])
        p(f"OK: sot_loaded path={sot_path} sot_required_count={len(sot_req) if isinstance(sot_req, list) else 'NA'}")
    else:
        p(f"SKIP: sot_missing path={sot_path}")

    for meta in selected:
        rid = meta.get("id")
        nm = meta.get("name")
        if not isinstance(rid, int):
            p(f"SKIP: ruleset missing id name={nm}")
            continue
        full = get_ruleset(owner, repo, rid)
        if not full:
            p(f"ERROR: cannot fetch ruleset id={rid}")
            continue
        req = extract_required_status_checks(full)
        if not req:
            p(f"SKIP: no required_status_checks rule id={rid} name={nm}")
            continue

        required_items = req.get("required_status_checks", [])
        required_ctx = sorted({it.get("context") for it in required_items if isinstance(it, dict) and isinstance(it.get("context"), str)})
        p(f"OK: ruleset_required_count={len(required_ctx)} id={rid} name={nm}")

        ghost = sorted([c for c in required_ctx if c not in set(observed)])
        if ghost:
            p(f"WARN: ghost_required_contexts count={len(ghost)} id={rid} name={nm}")
            for c in ghost:
                p(f"WARN: ghost {c}")
        else:
            p(f"OK: no_ghost_required_contexts id={rid} name={nm}")

        if sot and isinstance(sot.get("required_status_checks"), list):
            sot_ctx = sorted({it.get("context") for it in sot["required_status_checks"] if isinstance(it, dict) and isinstance(it.get("context"), str)})
            extra_in_ruleset = sorted([c for c in required_ctx if c not in set(sot_ctx)])
            missing_in_ruleset = sorted([c for c in sot_ctx if c not in set(required_ctx)])

            if extra_in_ruleset:
                p(f"WARN: ruleset_has_extra_vs_sot count={len(extra_in_ruleset)} id={rid}")
                for c in extra_in_ruleset:
                    p(f"WARN: extra {c}")
            else:
                p(f"OK: no_extra_vs_sot id={rid}")

            if missing_in_ruleset:
                p(f"WARN: ruleset_missing_vs_sot count={len(missing_in_ruleset)} id={rid}")
                for c in missing_in_ruleset:
                    p(f"WARN: missing {c}")
            else:
                p(f"OK: no_missing_vs_sot id={rid}")

if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception as e:
        p(f"ERROR: unhandled_exception {e}")
        # 例外で止めない（終了コード依存にしない）
