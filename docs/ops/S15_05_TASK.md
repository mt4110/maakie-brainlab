# S15-05 TASK: AI Work v1 — deterministic local AI lane + evidence rails

## Phase 0 — Preflight (STOP early)
- [ ] IF `git status --porcelain` is NOT empty THEN STOP (error: paste output)
- [ ] ELSE continue

## Phase 1 — Locate AI entrypoint (FOR + break)
- [ ] FOR file in:
  - [ ] src/local_llm.py
  - [ ] src/ask.py
  - [ ] eval/run_eval.py
  - [ ] infra/run-llama-server.sh
  - [ ] prompts/system.md
  - [ ] prompts/rag.md
  - [ ] docs/rules/AI_TEXT_GUARD.md
- [ ] IF file exists THEN mark "FOUND" and continue
- [ ] ELSE skip with 1-line reason
- [ ] IF none FOUND THEN STOP (error: "AI entrypoint missing")

## Phase 2 — Determinism locks (must)
- [ ] IF any run depends on current time for semantic output THEN error + remove it
- [ ] IF iteration order depends on filesystem order THEN sort paths
- [ ] IF randomness exists THEN set fixed seed (single source of truth)
- [ ] IF network call exists in AI lane THEN STOP (offline-only)

## Phase 3 — Hygiene locks (must)
- [ ] IF outputs can be written under repo root THEN reroute to `.local/ai_runs/**` or tempdir
- [ ] IF `.local/ai_runs/**` is used THEN ensure:
  - [ ] directory created safely (mkdir fail-fast)
  - [ ] file names deterministic (no wallclock in filenames unless purely log)

## Phase 4 — Evidence rails (must)
- [ ] Record inputs (prompt, config, model id, seed) as a manifest (json or tsv)
- [ ] Record outputs (response, metrics) as jsonl
- [ ] Record sha256 for each artifact
- [ ] IF any evidence file is missing THEN STOP

## Phase 5 — Tests (minimal)
- [ ] Run fast unit tests for AI lane (existing test framework)
- [ ] IF tests are flaky/time-based THEN skip with 1-line reason + create deterministic alternative

## Phase 6 — Gate (the truth machine)
- [ ] `make test`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [ ] IF preflight says dirty tree THEN STOP (hygiene regression)
- [ ] ELSE capture SUBMIT filename + SHA256 into SOT

## Phase 7 — PR rail
- [ ] `git push -u origin s15-05-ai-work-v1`
- [ ] `gh pr create --fill`
