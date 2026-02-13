# S15-05 TASK: AI Work v1 — deterministic local AI lane + evidence rails

## Phase 0 — Preflight (STOP early)
- [x] IF `git status --porcelain` is NOT empty THEN STOP (error: paste output)
- [x] ELSE continue

## Phase 1 — Locate AI entrypoint (FOR + break)
- [x] FOR file in:
  - [x] src/local_llm.py
  - [x] src/ask.py
  - [x] eval/run_eval.py
  - [x] infra/run-llama-server.sh
  - [x] prompts/system.md
  - [x] prompts/rag.md
  - [x] docs/rules/AI_TEXT_GUARD.md
- [x] IF file exists THEN mark "FOUND" and continue
- [ ] ELSE skip with 1-line reason
- [ ] IF none FOUND THEN STOP (error: "AI entrypoint missing")

## Phase 2 — Determinism locks (must)
- [x] IF any run depends on current time for semantic output THEN error + remove it
- [x] IF iteration order depends on filesystem order THEN sort paths (Checked src/ask.py)
- [x] IF randomness exists THEN set fixed seed (Set temperature=0.0 default)
- [x] IF network call exists in AI lane THEN STOP (offline-only verified)

## Phase 3 — Hygiene locks (must)
- [x] IF outputs can be written under repo root THEN reroute to `.local/ai_runs/**` or tempdir
- [x] IF `.local/ai_runs/**` is used THEN ensure:
  - [x] directory created safely (mkdir fail-fast)
  - [x] file names deterministic (no wallclock in filenames unless purely log)

## Phase 4 — Evidence rails (must)
- [x] Record inputs (prompt, config, model id, seed) as a manifest (json or tsv)
- [x] Record outputs (response, metrics) as jsonl
- [x] Record sha256 for each artifact
- [x] IF any evidence file is missing THEN STOP

## Phase 5 — Tests (minimal)
- [x] Run fast unit tests for AI lane (existing test framework)
- [ ] IF tests are flaky/time-based THEN skip with 1-line reason + create deterministic alternative (N/A)

## Phase 6 — Gate (the truth machine)
- [x] `make test`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [x] IF preflight says dirty tree THEN STOP (hygiene regression)
- [x] ELSE capture SUBMIT filename + SHA256 into SOT
  - SUBMIT: review_bundle_20260213_182558.tar.gz
  - SHA256: af54a9773362f150d3f512798d535bc9c7b495f0747615d676d1069a92c17904

## Phase 7 — PR rail
- [ ] `git push -u origin s15-05-ai-work-v1`
- [ ] `gh pr create --fill`
