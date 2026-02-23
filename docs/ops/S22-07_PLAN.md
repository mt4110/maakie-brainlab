PLAN（Pseudo）

Inputs
S22-06 で導入済み：OBS_FORMAT_v1 / obs_writer.py / scripts/il_entry.py（既に存在）

Goal
IL入口を scripts/il_entry.py に一本化し、毎回 verify を強制

Non-Goals
重い eval wall / seed-mini は触らない（P8でやる）
大規模リファクタ禁止（入口一本化に必要な範囲だけ）

Flow（STOP=1 制御）
INIT:
  STOP=0
  ROOT = git rev-parse --show-toplevel (or ERROR + STOP=1)
  OBS_DIR = .local/obs/s22-07_<UTC_TS> (mkdir)

DISCOVER_ENTRYPOINTS:
  if STOP==0:
    for pattern in ["il_entry", "il_exec", "il_guard", "entry", "runner"]:
      rg in scripts/ docs/ Makefile (log results)
    if no duplicates found:
      OK: already single-entry (still proceed to contract/runbook/test)
    else:
      list candidates -> decide wrapper/deprecate policy (doc first)

SPEC_FREEZE:
  if STOP==0:
    write docs/il/IL_ENTRY_CONTRACT_v1.md (CLI I/F, inputs/outputs, invariants)
    write docs/ops/IL_ENTRY_RUNBOOK.md (smoke->verify-only, logs, grep rules)
    if docs not written:
      ERROR + STOP=1

IMPLEMENT_SINGLE_ENTRY:
  if STOP==0:
    update scripts/il_entry.py:
      try:
        - ALWAYS: canonicalize/validate step first
        - if validate ERROR: print ERROR + STOP-like behavior inside program (no SystemExit)
        - if execute requested and validate OK: execute
        - ALWAYS: write obs log (OBS_FORMAT_v1)
      catch(Exception):
        print ERROR (no raise SystemExit)
      finally:
        print OK/ERROR summary
    for each legacy entrypoint found:
      convert to thin wrapper that calls il_entry.py OR emit SKIP with deprecation note
      (must not break existing calls)

SMOKE_TEST:
  if STOP==0:
    add tests/test_il_entry_smoke.py:
      - no assert
      - no exception termination
      - writes OK/ERROR lines
      - tests 2 cases: good IL and bad IL (fixturesは既存から流用、無ければ docs/il/examples を探索して使用)
    integrate into existing verify flow:
      - prefer Makefile / existing verify script discovered via rg
      - if integration uncertain: provide runbook command only（壊さない）

LIGHT_VERIFY:
  if STOP==0:
    run minimal commands, each isolated:
      - python il_entry.py --help
      - smoke test
    if CPU heavy symptoms:
      SKIP: heavy verification (reason logged)

STATUS_UPDATE:
  update docs/ops/STATUS.md:
    S22-06 = 100% (Merged, PR#83)
    S22-07 = 1% (WIP)
DONE:
  print OK: plan completed (even if STOP==1, emit final summary)
