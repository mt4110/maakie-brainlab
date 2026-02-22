<<<<<<< HEAD
# S22-05 PLAN — P6 IL Entry Single Entry + Always Verify
=======
# S22-05 PLAN — P6 IL Entry Single Entry + Always Verify [AMBI-v1]
>>>>>>> s22-05-il-entry-unify-always-verify-v1

## Goal
ILの入口を一本化し、毎回 validate/canonicalize → execute → artifacts verify を固定順で通す。
失敗しても落ちない（exit無し）。判定はログ（OK/ERROR/SKIP）だけ。

## Scope (Files)
- NEW: scripts/il_entry.py
- NEW: scripts/il_entry_smoke.py
- NEW: docs/il/IL_ENTRY_CONTRACT_v1.md
- NEW: docs/ops/IL_ENTRY_RUNBOOK.md
- USE: src/il_validator.py (ILValidator / ILCanonicalizer)
- USE: src/il_executor.py  (execute_il)
- KEEP: scripts/il_exec_run.py (legacy runner; deprecate in docs)

## Invariants
- exit / sys.exit / SystemExit / assert を使わない
- 例外は catch して ERROR を出す（落ちない）
- 後続ステップは STOP=1 で SKIP（理由を必ず1行）
- “重い処理”は別ステップに分離（常用スモーク vs 最終検証）

## PLAN (Pseudo)
STOP=0

if repo_root not found:
  print ERROR
  STOP=1

if STOP==0:
  for each required_path in [
    "src/il_validator.py",
    "src/il_executor.py",
    "scripts/il_exec_run.py"
  ]:
    if path missing:
      print ERROR with path
      STOP=1
      break
    else:
      print OK with path
      continue

if STOP==0:
  try:
    write docs/il/IL_ENTRY_CONTRACT_v1.md
    print OK
  catch e:
    print ERROR
    STOP=1

if STOP==0:
  try:
    implement scripts/il_entry.py
      - parse args: il_path, out_dir, fixture_db_path(optional)
      - validate/canonicalize via src/il_validator.py
      - execute via src/il_executor.execute_il
      - verify artifacts (light): out_dir + report existence + minimal keys
      - print OK/ERROR/SKIP lines only
      - never raise (catch all)
    print OK
  catch e:
    print ERROR
    STOP=1

if STOP==0:
  try:
    implement scripts/il_entry_smoke.py (light)
      - good IL -> OK
      - bad IL  -> ERROR (but process continues)
      - always prints summary and returns normally
    print OK
  catch e:
    print ERROR
    STOP=1

if STOP==0:
  try:
    write docs/ops/IL_ENTRY_RUNBOOK.md
      - how to run smoke (fast)
      - how to run heavy verify-only (separate)
    print OK
  catch e:
    print ERROR
    STOP=1

if STOP==0:
  run light verification (fast)
  if log indicates FAIL:
    print ERROR and STOP=1
  else:
    print OK

if STOP==0:
  (optional/heavy) run verify-only / reviewpack at end
  parse logs; print OK/ERROR
