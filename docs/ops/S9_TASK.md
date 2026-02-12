# S9 Task — Pack Diff / Audit Comparability (Ambi-run)
Last updated: 2026-02-13 (JST)

## Legend (control keywords)
- if / else if / else
- for / continue / break
- skip: (allowed non-fatal bypass; must be justified)
- error: (hard failure; stop immediately)
- STOP: (explicit stop condition)

---

## 0) Preflight (do not skip)
- [ ] if `git status -sb` is not clean → error: "working tree not clean" → STOP
- [ ] if current branch is not main → `git switch main`
- [ ] `git pull --ff-only`
- [ ] `git fetch origin --prune`
- [ ] `make ci-test`
- [ ] if `make ci-test` fails → error: "baseline CI failed" → STOP
- [ ] Run verify-only baseline:
  - [ ] if repo has a known verify-only command in docs/ops or RUNBOOK:
    - [ ] run it
  - [ ] else:
    - [ ] search: `rg -n "verify-only" -S .`
    - [ ] if found usage → run that exact command
    - [ ] else → error: "verify-only command not located" → STOP
- [ ] if verify-only baseline fails → error: "verify-only baseline failed" → STOP

---

## 1) Branch (S9 kickoff)
- [ ] `git switch -c feature/s9-pack-diff-audit-compare`
- [ ] if branch already exists:
  - [ ] `git switch feature/s9-pack-diff-audit-compare`
  - [ ] continue

---

## 2) Contract discovery (S8 reuse; do not reinvent)
Goal: locate how bundles are extracted + how raw sha256 guard is validated.

- [ ] Find bundle extract code:
  - [ ] `rg -n "tar|gzip|archive|Extract|Untar|bundle" internal cmd -S`
  - [ ] if found relevant function(s) → note exact file path(s) for reuse
  - [ ] else → error: "bundle extract not found" → STOP

- [ ] Find raw sha256 guard code:
  - [ ] `rg -n "sha256|SHA256|shasum|hash guard|logs/raw" internal -S`
  - [ ] if found guard verify function(s) → note exact file path(s) for reuse
  - [ ] else → error: "raw sha256 guard not found" → STOP

- [ ] Find portable logs contract:
  - [ ] `rg -n "logs/portable|portable view" -S internal docs`
  - [ ] if docs explain portable contract → keep it unchanged
  - [ ] else → continue (portable dir existence is still mandatory in diff)

---

## 3) Docs first (boundary lines fixed before code)
- [ ] Edit:
  - [ ] `docs/ops/S9_PLAN.md`
  - [ ] `docs/ops/S9_TASK.md`
- [ ] if these files do not exist → create them (content from Sora-chan message)
- [ ] Ensure Plan includes:
  - [ ] comparable set boundary (`logs/portable/**` etc.)
  - [ ] determinism rules (sorted slash paths, newline normalization)
  - [ ] exit code contract (0/1/2)
- [ ] if scope is ambiguous → error: "diff scope boundary not fixed" → STOP

---

## 4) Implement core diff (portable-first)
### 4.1 Files to edit/create (absolute path derivation)
Use:
- `cd "$(git rev-parse --show-toplevel)"` then edit these:
  - `cmd/reviewpack/main.go`
  - `internal/reviewpack/diff.go`
  - `internal/reviewpack/diff_test.go`

### 4.2 Core behaviors (portable)
- [ ] Implement `reviewpack diff` subcommand wiring in `cmd/reviewpack/main.go`
  - [ ] if command framework exists (cobra/flag/subcommands) → follow existing style
  - [ ] else → error: "CLI framework unclear" → STOP

- [ ] In `internal/reviewpack/diff.go` implement:
  - [ ] Extract A/B bundles to temp dirs (reuse existing extract code)
  - [ ] Validate required dirs:
    - [ ] if `logs/portable/` missing in either side → error → STOP
  - [ ] Build file list for `logs/portable/**`
    - [ ] for each file:
      - [ ] record relative path as slash path
      - [ ] record content hash or bytes
  - [ ] Compare sets:
    - [ ] added / removed / modified
  - [ ] For modified files:
    - [ ] if file is binary-ish:
      - [ ] skip: unified diff; output "binary changed"
      - [ ] continue
    - [ ] else:
      - [ ] compute line-based unified diff (deterministic)
  - [ ] Output ordering:
    - [ ] sort paths lexicographically (slash paths)
    - [ ] summary first, details next

- [ ] Exit code:
  - [ ] if no diffs → return 0
  - [ ] else if diffs found → return 1
  - [ ] else on error → return 2

### 4.3 Optional behaviors (raw hashes)
- [ ] if implementing `--kind raw|both`:
  - [ ] reuse guard validation function (must not change it)
  - [ ] derive raw hash list deterministically
  - [ ] compare and report (added/removed/changed)
- [ ] else:
  - [ ] skip: raw mode (acceptable for first PR ONLY if docs say “portable-first minimal”)
  - [ ] BUT: if you skip raw mode, you MUST still validate guard at least once (see Step 6)

---

## 5) Tests (determinism + edge cases)
- [ ] Add unit tests in `internal/reviewpack/diff_test.go`
- [ ] Cases:
  - [ ] if both bundles identical → exit 0, empty diff
  - [ ] if portable file added → exit 1, reports "added"
  - [ ] if portable file changed (text) → exit 1, includes unified diff
  - [ ] if portable missing → exit 2 (error)
  - [ ] determinism test:
    - [ ] run diff twice (same inputs) → outputs identical (byte compare)

- [ ] if any test is flaky / order-dependent → error: "nondeterministic diff" → STOP

---

## 6) Proof (bundle-to-bundle demonstration)
Goal: show diff works on real artifacts without breaking verify-only.

- [ ] Generate two bundles:
  - [ ] for i in [A,B]:
    - [ ] run the existing pack command that produces a bundle
    - [ ] record produced artifact path
    - [ ] if pack command requires inputs:
      - [ ] ensure B differs from A by a minimal, intentional change (e.g., add a harmless note that affects portable logs)
      - [ ] else → continue
- [ ] Run:
  - [ ] `reviewpack diff <bundleA> <bundleB>`
- [ ] if output says no diffs but you intentionally changed something → error: "diff false negative" → STOP
- [ ] Run verify-only again (must be unchanged):
  - [ ] if verify-only fails → error: "verify-only regressed" → STOP
- [ ] Validate guard:
  - [ ] if guard check fails unexpectedly → error: "guard regression" → STOP

---

## 7) Pre-PR cleanup + evidence
- [ ] `make ci-test`
- [ ] if fails → STOP
- [ ] verify-only again → must PASS
- [ ] `git status -sb` must be clean after add/commit steps
- [ ] Prepare a short evidence note in docs (or a local evidence log file) describing:
  - [ ] bundleA path, bundleB path (or redacted)
  - [ ] diff output summary
  - [ ] verify-only PASS proof

---

## 8) Commit discipline (small, reversible)
- [ ] Commit-1: `docs(ops): add S9 plan/task for pack diff`
- [ ] Commit-2: `feat(reviewpack): add bundle diff (portable-first)`
- [ ] Commit-3: `test(reviewpack): add diff determinism tests`
- [ ] if any commit mixes docs+code+tests excessively → break it up (continue only after split)

---

## 9) Push & PR
- [ ] `git push -u origin feature/s9-pack-diff-audit-compare`
- [ ] Create PR (title example):
  - [ ] `reviewpack: S9 comparable audit (bundle diff portable-first)`
- [ ] Ensure PR body includes:
  - [ ] scope boundary (portable-first)
  - [ ] invariants (verify-only unchanged)
  - [ ] evidence summary

---

## STOP conditions summary
- STOP if verify-only regresses
- STOP if guard semantics change
- STOP if diff output is nondeterministic
- STOP if contract boundary is not documented
