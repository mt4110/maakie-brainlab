#!/usr/bin/env bash
# scripts/ops/gh_ruleset_doctor.sh
# exit禁止運用: exit / set -e / trap EXIT など禁止。STOPフラグで制御。
# 依存: gh (任意), python3 (推奨)

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
STOP="0"

if [ -z "$ROOT" ]; then
  echo "ERROR: not in repo"
  STOP="1"
else
  cd "$ROOT" 2>/dev/null || true
  echo "OK: repo=$ROOT"
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OBS=".local/obs/gh_ruleset_doctor_${TS}"
mkdir -p "$OBS" 2>/dev/null || true
echo "OK: obs_dir=$OBS"

GH="$(command -v gh 2>/dev/null || true)"
if [ "$STOP" = "0" ]; then
  if [ -z "$GH" ]; then
    echo "SKIP: gh not found (install GitHub CLI to enable ruleset check)" | tee "$OBS/01_skip.txt" || true
    STOP="1"
  else
    echo "OK: gh=$GH" | tee "$OBS/01_gh.txt" || true
  fi
fi

# gh auth status (string match; no exit-code control)
if [ "$STOP" = "0" ]; then
  AUTH="$($GH auth status 2>&1 || true)"
  echo "$AUTH" > "$OBS/02_auth_status.txt"
  case "$AUTH" in
    *"Logged in to github.com"*)
      echo "OK: gh authed" | tee "$OBS/02_auth_ok.txt" || true
      ;;
    *)
      echo "SKIP: gh not authed (run: gh auth login)" | tee "$OBS/02_auth_skip.txt" || true
      STOP="1"
      ;;
  esac
fi

REPO=""
DEF_BRANCH="main"
SHA=""

if [ "$STOP" = "0" ]; then
  REPO="$($GH repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
  if [ -z "$REPO" ]; then
    echo "ERROR: cannot detect repo via gh (are you in the right repo?)" | tee "$OBS/10_repo.txt" || true
    STOP="1"
  else
    echo "OK: repo=$REPO" | tee "$OBS/10_repo.txt" || true
  fi
fi

if [ "$STOP" = "0" ]; then
  DEF_BRANCH="$($GH repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || true)"
  if [ -z "$DEF_BRANCH" ]; then
    DEF_BRANCH="main"
    echo "WARN: defaultBranchRef unknown -> fallback=main" | tee "$OBS/11_branch.txt" || true
  else
    echo "OK: default_branch=$DEF_BRANCH" | tee "$OBS/11_branch.txt" || true
  fi
fi

if [ "$STOP" = "0" ]; then
  git fetch origin --prune 2>/dev/null | tee "$OBS/12_fetch.log" || true
  SHA="$(git rev-parse "origin/$DEF_BRANCH" 2>/dev/null || true)"
  if [ -z "$SHA" ]; then
    SHA="$(git rev-parse "$DEF_BRANCH" 2>/dev/null || true)"
  fi

  if [ -z "$SHA" ]; then
    echo "ERROR: cannot resolve SHA for branch=$DEF_BRANCH" | tee "$OBS/13_sha.txt" || true
    STOP="1"
  else
    echo "OK: sha=$SHA" | tee "$OBS/13_sha.txt" || true
  fi
fi

# Fetch check-runs (head commit)
if [ "$STOP" = "0" ]; then
  $GH api "repos/$REPO/commits/$SHA/check-runs?per_page=100" > "$OBS/20_check_runs_head.json" 2>/dev/null || true
  SZ="$(wc -c < "$OBS/20_check_runs_head.json" 2>/dev/null | tr -d " " || true)"
  if [ -z "$SZ" ] || [ "$SZ" = "0" ]; then
    echo "WARN: check-runs response empty (insufficient permission or API change?)" | tee "$OBS/21_check_runs_warn.txt" || true
  else
    echo "OK: wrote check-runs head bytes=$SZ" | tee "$OBS/21_check_runs_ok.txt" || true
  fi
fi

# Fetch rulesets list
if [ "$STOP" = "0" ]; then
  $GH api "repos/$REPO/rulesets?per_page=100" > "$OBS/30_rulesets_list.json" 2>/dev/null || true
  SZ="$(wc -c < "$OBS/30_rulesets_list.json" 2>/dev/null | tr -d " " || true)"
  if [ -z "$SZ" ] || [ "$SZ" = "0" ]; then
    echo "WARN: rulesets list empty (no rulesets or permission?)" | tee "$OBS/31_rulesets_warn.txt" || true
  else
    echo "OK: wrote rulesets list bytes=$SZ" | tee "$OBS/31_rulesets_ok.txt" || true
  fi
fi

# Parse + compare in python (no sys.exit / no raise for control)
if [ "$STOP" = "0" ]; then
  export OBS
  python3 - <<'PY' 2>/dev/null | tee "$OBS/40_compare.log" || true
import os, json
from pathlib import Path

obs = Path(os.environ["OBS"])
p_runs = obs / "20_check_runs_head.json"
p_list = obs / "30_rulesets_list.json"

def safe_load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: cannot parse json {p} ({e})")
        return None

runs = safe_load(p_runs) if p_runs.exists() else None
lst  = safe_load(p_list) if p_list.exists() else None

observed = set()
if isinstance(runs, dict):
    for cr in runs.get("check_runs", []) or []:
        name = cr.get("name")
        if isinstance(name, str) and name.strip():
            observed.add(name.strip())

print(f"OK: observed_check_runs_count={len(observed)}")
if len(observed) > 0:
    # keep it light: show up to 30
    sample = sorted(list(observed))[:30]
    for s in sample:
        print(f"OK: observed={s}")
else:
    print("WARN: no observed check-runs (may be permissions / no checks on that commit)")

ruleset_ids = []
if isinstance(lst, list):
    for r in lst:
        rid = r.get("id")
        if isinstance(rid, int):
            ruleset_ids.append(rid)

print(f"OK: rulesets_count={len(ruleset_ids)}")
(out_ids := (obs / "41_ruleset_ids.txt")).write_text("\n".join(str(x) for x in ruleset_ids), encoding="utf-8")
print(f"OK: wrote {out_ids}")

# Extract required contexts from *list* response if present (some APIs include rules, some don't)
required = {}
if isinstance(lst, list):
    for r in lst:
        name = r.get("name") or f"id={r.get('id')}"
        reqs = []
        for rule in (r.get("rules") or []):
            if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
                params = rule.get("parameters") or {}
                for item in (params.get("required_status_checks") or []):
                    ctx = item.get("context") if isinstance(item, dict) else None
                    if isinstance(ctx, str) and ctx.strip():
                        reqs.append(ctx.strip())
        if reqs:
            required[name] = sorted(set(reqs))

if required:
    print(f"OK: required_contexts_found_in_list_response={sum(len(v) for v in required.values())}")
else:
    print("WARN: rulesets list response had no embedded required checks (will need per-ruleset fetch)")
PY
fi

# Per-ruleset fetch only if needed (i.e., list had no embedded rules)
NEED_DETAIL="0"
if [ -f "$OBS/40_compare.log" ]; then
  LOG="$(cat "$OBS/40_compare.log" 2>/dev/null || true)"
  case "$LOG" in
    *"will need per-ruleset fetch"*) NEED_DETAIL="1" ;;
    *) NEED_DETAIL="0" ;;
  esac
fi

if [ "$STOP" = "0" ] && [ "$NEED_DETAIL" = "1" ]; then
  IDS="$(cat "$OBS/41_ruleset_ids.txt" 2>/dev/null || true)"
  if [ -z "$IDS" ]; then
    echo "SKIP: no ruleset ids to fetch" | tee "$OBS/50_detail_skip.txt" || true
  else
    echo "OK: fetching ruleset details (light loop)" | tee "$OBS/50_detail_start.txt" || true
    for rid in $IDS; do
      # 1 ruleset = 1 small json
      $GH api "repos/$REPO/rulesets/$rid" > "$OBS/51_ruleset_${rid}.json" 2>/dev/null || true
      BY="$(wc -c < "$OBS/51_ruleset_${rid}.json" 2>/dev/null | tr -d " " || true)"
      if [ -z "$BY" ] || [ "$BY" = "0" ]; then
        echo "WARN: ruleset detail empty id=$rid" | tee -a "$OBS/52_detail_warn.txt" || true
        continue
      fi
      echo "OK: ruleset detail id=$rid bytes=$BY" | tee -a "$OBS/52_detail_ok.txt" || true
    done
  fi
fi

# Final compare (detail jsons -> required contexts -> diff)
if [ "$STOP" = "0" ]; then
  export OBS
  python3 - <<'PY' 2>/dev/null | tee "$OBS/60_report.log" || true
import os, json, glob
from pathlib import Path

obs = Path(os.environ["OBS"])

def safe_load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: cannot parse {p} ({e})")
        return None

runs = safe_load(obs / "20_check_runs_head.json") if (obs / "20_check_runs_head.json").exists() else None
observed = set()
if isinstance(runs, dict):
    for cr in runs.get("check_runs", []) or []:
        n = cr.get("name")
        if isinstance(n, str) and n.strip():
            observed.add(n.strip())

# collect required contexts from detail files if they exist
required_contexts = {}  # key: ruleset_name, val: set(context)
detail_files = sorted(glob.glob(str(obs / "51_ruleset_*.json")))
if detail_files:
    for fp in detail_files:
        j = safe_load(fp)
        if not isinstance(j, dict):
            continue
        rname = j.get("name") or f"id={j.get('id')}"
        reqs = set()
        for rule in (j.get("rules") or []):
            if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
                params = rule.get("parameters") or {}
                for item in (params.get("required_status_checks") or []):
                    if isinstance(item, dict):
                        ctx = item.get("context")
                        if isinstance(ctx, str) and ctx.strip():
                            reqs.add(ctx.strip())
        if reqs:
            required_contexts[rname] = reqs

# fallback: if no detail files, try list response parse
if not required_contexts and (obs / "30_rulesets_list.json").exists():
    lst = safe_load(obs / "30_rulesets_list.json")
    if isinstance(lst, list):
        for r in lst:
            rname = r.get("name") or f"id={r.get('id')}"
            reqs = set()
            for rule in (r.get("rules") or []):
                if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
                    params = rule.get("parameters") or {}
                    for item in (params.get("required_status_checks") or []):
                        if isinstance(item, dict):
                            ctx = item.get("context")
                            if isinstance(ctx, str) and ctx.strip():
                                reqs.add(ctx.strip())
            if reqs:
                required_contexts[rname] = reqs

print(f"OK: observed_count={len(observed)}")
print(f"OK: rulesets_with_required_checks={len(required_contexts)}")

ghost_total = 0
for rname, reqs in sorted(required_contexts.items(), key=lambda x: x[0].lower()):
    missing = sorted([c for c in reqs if c not in observed])
    print(f"OK: ruleset={rname} required={len(reqs)} missing_in_head={len(missing)}")
    if missing:
        ghost_total += len(missing)
        for c in missing[:50]:
            print(f"WARN: missing_context={c} (ruleset={rname})")

if ghost_total == 0:
    print("OK: no missing contexts detected on HEAD commit check-runs")
else:
    print(f"WARN: missing_contexts_total={ghost_total}")
    print("HINT: missing does not always mean ghost; it may be conditional. If it keeps missing across several commits, it is likely ghost.")
PY
fi

echo "OK: done stop=$STOP"
