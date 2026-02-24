# S22-09_PLAN.md
# S22-09(P8+P9): Eval Wall v2 taxonomy+metrics + Council design (design-only)
# Policy: stopless / no exit / no exception-halting / no status-code control
# Output truth: OK:/ERROR:/SKIP: lines + evidence in .local/obs/...

STATE:
  STOP = "0"
  ROOT = ""
  OBS  = ""
  BR   = "s22-09-eval-wall-v2-taxonomy-council-v1"

GOAL(P8):
  - IL/RAG failure taxonomy を固定し、計測(JSONL)に統合
  - 同一入力 -> 同一JSONL(sha一致) を保証できる最小条件を定義＆テストする

GOAL(P9):
  - Council(多モデル合議) を “必要になってから” 差し込める契約を設計だけで固める
  - 実装はしない（トリガー/上限/成果物/料金ガードレールまで文書化）

STEP 0: locate repo
  try:
    ROOT = `git rev-parse --show-toplevel`
    if ROOT == "":
      print ERROR and set STOP=1
    else:
      cd ROOT
      print OK repo
  catch:
    print ERROR and set STOP=1

STEP 1: create OBS dir (always)
  try:
    TS = utc timestamp
    OBS = ".local/obs/s22-09_" + TS
    mkdir -p OBS
    print OK obs_dir
  catch:
    print ERROR and set STOP=1

STEP 2: path reality check (no assumptions)
  if STOP==0:
    for each MUST_FILE in [
      "docs/ops/S22-09_PLAN.md",
      "docs/ops/S22-09_TASK.md",
      "docs/ops/STATUS.md",
      "docs/evidence/EVAL_WALL_V2.md",
      "tests/test_eval_wall_v2_smoke.py",
      "docs/il/IL_COUNCIL_CONTRACT_v1.md",
      "docs/ops/MULTIMODEL_POLICY_v1.md"
    ]:
      if file exists:
        print OK exists path=MUST_FILE
      else:
        print SKIP missing path=MUST_FILE (will create)

STEP 3: define “execution mode contract” FIRST (the pitfall killer)
  if STOP==0:
    edit docs/evidence/EVAL_WALL_V2.md:
      - Define terms: validate-only / run / classify / measure
      - validate-only MUST:
          * no executor/opcode execution
          * no network
          * no writes outside OBS (ideally no writes at all)
      - run MUST:
          * allowed writes ONLY under OBS
          * produces JSONL + summary with fixed schema
      - Determinism scope:
          * same input + same version + same flags => same JSONL sha256
      - Record taxonomy list and version tag (TAXONOMY_v1)

STEP 4: failure taxonomy integration (P8)
  if STOP==0:
    define failure tags (TAXONOMY_v1):
      - schema / contract / opcode / normalization / index / search / cite
    integrate into:
      - dataset labeling (seed-mini re-tag)
      - metrics output (summary.json counts by tag)
      - RESULT_SCHEMA: ensure tag field location is stable and documented

STEP 5: “validate-only means no run” enforcement audit
  if STOP==0:
    discover entrypoints:
      - rg for "validate-only", "mode", "executor", "run", "eval wall"
      - list candidates to OBS/entrypoints.txt
    for each candidate entrypoint:
      - verify validate-only path does NOT call executor/run side-effects
      - if violation found:
          print ERROR and record to OBS/violations.txt
          set STOP=1 (do not proceed to measurement changes)

STEP 6: dataset + measurement (P8) in CPU-safe slices
  if STOP==0:
    slice policy:
      - smoke first: run minimal subset (seed-mini or first N cases)
      - full run later if smoke OK
    run 1 (smoke):
      - produce OBS/run1/*.jsonl + summary.json
      - compute sha256 and store OBS/run1/sha256.txt
    run 2 (same input, same flags):
      - produce OBS/run2/*.jsonl + summary.json
      - compute sha256 and compare with run1
      - if mismatch: print ERROR and STOP=1
      - else: print OK sha_match

STEP 7: tests (P8)
  if STOP==0:
    implement/update tests/test_eval_wall_v2_smoke.py:
      - ensure taxonomy tags appear
      - ensure schema fields exist
      - ensure determinism check helper can be executed in CI-like mode
    run tests in stopless wrapper:
      - capture output to OBS/test.log
      - decide PASS/FAIL by parsing text (not exit code)

STEP 8: Council design docs (P9, design-only)
  if STOP==0:
    write docs/il/IL_COUNCIL_CONTRACT_v1.md:
      - opcodes: COUNCIL_PLAN / COUNCIL_RUN / COUNCIL_DECIDE (spec only)
      - inputs/outputs schema, artifact paths, evidence requirements
      - trigger definition (when to invoke)
      - cost/time ceilings (hard limits)
      - safety: forbid infinite loops, forbid unbounded tool calls
    write docs/ops/MULTIMODEL_POLICY_v1.md:
      - operational policy: when allowed, who/what approves, logs
      - budget/timebox default + override process
      - “do nothing is OK” policy (avoid pointless spend)

STEP 9: STATUS update + progress meter
  if STOP==0:
    update docs/ops/STATUS.md:
      - S22-08: 100% (Merged)
      - S22-09: start 1% (WIP) after kickoff commit
    record "progress=%" line in PR body later

STEP 10: final verify (lightweight first)
  if STOP==0:
    run make/verify targets if present (discover via `make -n` or rg in Makefile)
    heavy steps are split:
      - go test ./... (if needed)
      - python tests (targeted)
      - any bundle build only if required
    all commands are wrapped with `|| true`, judgement by logs

STEP 11: PR create (single PR for P8+P9)
  if STOP==0:
    prepare PR body in SOT/証拠スタイル (ガチガチ+短縮)
    include:
      - OBS paths
      - sha256 evidence
      - taxonomy version
      - determinism result

END:
  print OK done stop=STOP
