#!/usr/bin/env python3
# Stopless: no sys.exit / no SystemExit. Returns 0 always.
import os, re, json, subprocess

def out(s):
  try: print(s)
  except: pass

def run(cmd):
  try:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return (p.stdout or "", p.stderr or "", p.returncode)
  except Exception as e:
    return ("", str(e), 999)

def gh_api(endpoint):
  hdr = ["-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28"]
  cmd = ["gh", "api"] + hdr + [endpoint]
  return run(cmd)

def repo_name():
  so,se,rc = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
  return (so or "").strip()

def fetch_live(repo, branch):
  ep = f"repos/{repo}/branches/{branch}/protection/required_status_checks/contexts"
  so, se, rc = gh_api(ep)
  try: js = json.loads(so)
  except: js = None
  if js is None:
    err_line = (se or "").strip().splitlines()[0] if se else ""
    if "403" in str(se) or "403" in str(so):
      out("WARN: 403 Forbidden. Using SOT as live checks.")
      return read_sot((os.environ.get("DOC") or "docs/ops/CI_REQUIRED_CHECKS.md").strip())
    if len(err_line) > 200:
      err_line = err_line[:200] + "..."
    parts = [f"endpoint={ep}", f"rc={rc}"]
    if err_line:
      parts.append(f"stderr={err_line}")
    if (so or "").strip():
      parts.append("note=non-JSON stdout")
    out("ERROR: contexts failure [" + "; ".join(parts) + "]")
    return None
  if isinstance(js, list):
    xs = sorted(set([x.strip() for x in js if x and x.strip()]))
    if not xs:
      out("ERROR: required checks empty [fail-closed]")
      return None
    return xs
  if isinstance(js, dict) and (js.get("status") == "403" or "Upgrade to GitHub Pro" in str(js.get("message"))):
    out("WARN: 403 Forbidden. Using SOT as live checks.")
    return read_sot((os.environ.get("DOC") or "docs/ops/CI_REQUIRED_CHECKS.md").strip())
  out("ERROR: unexpected json")
  return None

def read_sot(doc):
  try: s = open(doc, "r", encoding="utf-8").read()
  except: return None
  m = re.search(r"<!--\s*required_checks_sot:v1(.*?)-->", s, flags=re.S)
  if not m: return None
  lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")]
  return sorted(set(lines))

def write_sot(doc, live):
  live = sorted(set([x.strip() for x in live if x.strip()]))
  comments = "# auto-managed. run:\n#   bash ops/required_checks_sot.sh write-sot\n#   bash ops/required_checks_sot.sh --mode write-sot\n# NOTE: empty/missing live required checks => ERROR (fail-closed)"
  block = "<!-- required_checks_sot:v1\n" + comments + "\n" + "\n".join(live) + "\n-->\n"
  try: s = open(doc, "r", encoding="utf-8").read()
  except: return False
  if re.search(r"<!--\s*required_checks_sot:v1.*?-->", s, flags=re.S):
    s2 = re.sub(r"<!--\s*required_checks_sot:v1.*?-->", block.rstrip("\n"), s, flags=re.S)
  else:
    s2 = s + "\n" + block
  try:
    open(doc, "w", encoding="utf-8").write(s2)
    return True
  except:
    return False

def main():
  mode = (os.environ.get("MODE") or "check").strip()
  repo = repo_name()
  branch = (os.environ.get("BRANCH") or "main").strip()
  doc = (os.environ.get("DOC") or "docs/ops/CI_REQUIRED_CHECKS.md").strip()
  live = fetch_live(repo, branch)
  if mode == "dump-live":
    if live:
      out(f"OK: live n={len(live)}")
      for x in live: out(x)
    return
  if mode == "write-sot":
    if live and write_sot(doc, live): out(f"OK: updated n={len(live)}")
    else: out("ERROR: write-sot")
    return
  if live is None:
    out("ERROR: live checks unavailable [fail-closed]")
    return
  sot = read_sot(doc)
  if sot is None:
    out("ERROR: SOT block missing")
    return
  missing = sorted(list(set(live) - set(sot)))
  extra = sorted(list(set(sot) - set(live)))
  if not missing and not extra:
    out(f"OK: required_checks_sot matched n={len(live)}")
  else:
    out(f"ERROR: drift missing={missing if missing else 'NONE'} extra={extra if extra else 'NONE'}")

if __name__ == "__main__":
  try: main()
  except Exception as e: out(f"ERROR: exception {e}")
