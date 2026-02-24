#!/usr/bin/env python3
# stopless: no sys.exit, no argparse(SystemExit), no assert
import ast, sys
from pathlib import Path

FORBIDDEN_NAMES = {
  "subprocess","requests","urllib","socket","http",
  "il_executor","il_exec","executor","run_entry","run_entry_attempts",
  "os.system","os.popen",
}

def parse_args(argv):
  targets=[]
  seen=set()
  i=0
  while i < len(argv):
    a=argv[i]
    if a=="--targets" and i+1 < len(argv):
      raw=argv[i+1]
      for item in raw.split(","):
        t=item.strip()
        if not t:
          continue
        if t in seen:
          continue
        seen.add(t)
        targets.append(t)
      i += 2
      continue
    i += 1
  return targets

def build_alias_map(tree):
  amap={}
  for node in ast.walk(tree):
    if isinstance(node, ast.Import):
      for a in node.names:
        name=a.name
        asn=a.asname or name.split(".")[-1]
        amap[asn]=name
    if isinstance(node, ast.ImportFrom):
      mod=node.module or ""
      for a in node.names:
        nm=a.name
        asn=a.asname or nm
        if mod:
          amap[asn]=mod + "." + nm
  return amap

def call_name(node, amap):
  # get dotted name (best-effort + import alias resolution)
  if isinstance(node, ast.Name):
    n=node.id
    return amap.get(n, n)
  if isinstance(node, ast.Attribute):
    base = call_name(node.value, amap)
    if base:
      return base + "." + node.attr
    return node.attr
  return "" 

def is_validate_only_test(test_src: str) -> bool:
  s=test_src.lower()
  return ("validate" in s and "only" in s) or ("v_only" in s) or ("validate_only" in s)

def walk_validate_only_blocks(tree, source):
  # find if-blocks whose test mentions validate-only
  blocks=[]
  for node in ast.walk(tree):
    if isinstance(node, ast.If):
      try:
        t = ast.get_source_segment(source, node.test) or ""
      except Exception:
        t = ""
      if is_validate_only_test(t):
        blocks.append(node)
  return blocks

def scan_block_forbidden(block, amap):
  found=set()
  for node in ast.walk(block):
    if isinstance(node, ast.Call):
      n=call_name(node.func, amap)
      if n in FORBIDDEN_NAMES:
        found.add(n)
      # substring check (best-effort)
      for f in FORBIDDEN_NAMES:
        if f in n:
          found.add(n)
  return sorted(found)

def main():
  STOP="0"
  targets=parse_args(sys.argv[1:])
  if not targets:
    print("ERROR: missing --targets (comma-separated)")
    print("OK: done stop=1")
    return

  for t in targets:
    p=Path(t)
    if not p.exists():
      print(f"SKIP: missing target={t}")
      continue
    try:
      src=p.read_text(encoding="utf-8", errors="replace")
      tree=ast.parse(src)
      amap=build_alias_map(tree)
    except Exception as e:
      print(f"ERROR: parse_failed target={t} err={e}")
      STOP="1"
      continue

    blocks=walk_validate_only_blocks(tree, src)
    if not blocks:
      print(f"SKIP: no validate-only if-block found target={t}")
      continue

    ok=True
    for i,b in enumerate(blocks[:20]):  # CPU safety
      bad=scan_block_forbidden(b, amap)
      if bad:
        ok=False
        STOP="1"
        print(f"ERROR: forbidden calls inside validate-only target={t} block#{i} bad={bad}")
    if ok:
      print(f"OK: validate-only blocks clean target={t} blocks={len(blocks)}")

  print("OK: done stop="+STOP)

if __name__=="__main__":
  try:
    main()
  except Exception as e:
    print("ERROR: crash err="+e.__class__.__name__)
    print("OK: done stop=1")
