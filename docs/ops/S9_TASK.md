# S9 Task — Pack Diff Refinement “実体化” (Ambi-run)
Last updated: 2026-02-13 (JST)

## Control Keywords
- if / else if / else
- for / continue / break
- skip (must record reason)
- error (exit 2)
- STOP (no further steps)

---

## 0) Preflight (absolute must)
- [ ] `cd "$(git rev-parse --show-toplevel)"`
- [ ] if `git status --porcelain=v1` is not empty -> error "dirty tree" -> STOP
- [ ] `make ci-test`
- [ ] if fail -> error "baseline ci-test failed" -> STOP
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [ ] if fail -> error "verify-only baseline failed" -> STOP

---

## 1) Gate Checks (PR前ゲート; 먼저ここで落とす)
### 1.1 docs hygiene
- [ ] run: `bash ops/check_no_file_url.sh`
- [ ] run: `rg -n '^\`{4}carousel' docs walkthrough -S && { echo "NG: carousel"; exit 2; } || true`
- [ ] continue

### 1.2 CLI flags exist (help)
- [ ] run: `go run cmd/reviewpack/main.go diff --help 2>&1 | rg -n -- '(-|--)kind|(-|--)format'`
- [ ] if no match -> error "flags not wired" -> STOP
- [ ] continue

---

## 2) Implementation Tasks (no silent failure)
### 2.1 STOP rule: ban os.Exit/log.Fatal in diff logic
- [ ] if `rg -n 'os\.Exit\(|log\.Fatal' internal/reviewpack/diff.go -S` hits:
  - [ ] else if those are only in top-level main/app layer:
    - [ ] continue
  - [ ] else -> error "diff logic uses os.Exit/log.Fatal" -> STOP

### 2.2 Implement CLI contract
Files:
- `internal/reviewpack/app.go`
- `internal/reviewpack/flags.go`
- `internal/reviewpack/diff.go`

- [ ] if command wiring already exists:
  - [ ] ensure `diff --kind` and `diff --format` are parsed and passed down
  - [ ] continue
- [ ] else -> error "CLI wiring not found" -> STOP

- [ ] Define `runDiff(args) (code int)` style:
  - [ ] if your framework uses Run() returning int -> use it
  - [ ] else if Run() has no return -> adapt so exit occurs only at top-level
  - [ ] else -> error "cannot enforce exit code contract" -> STOP

### 2.3 Implement exit code contract strictly
- [ ] if no diffs -> return 0
- [ ] else if diffs found -> return 1
- [ ] else on any error -> return 2
- [ ] if any branch returns 1 on error -> error "error must be 2" -> STOP

### 2.4 Implement portable diff (portable-first)
- [ ] Validate `logs/portable/` exists in both bundles:
  - [ ] if missing -> error (2) -> STOP
- [ ] for each file under `logs/portable/**` (sorted):
  - [ ] read bytes; if err -> error (2)
  - [ ] normalize portable content (Step 2.6)
- [ ] diff engine:
  - [ ] prefer `diff -u` integration:
    - [ ] if `exec diff -u` fails because diff not found:
      - [ ] skip (record reason: "diff not available")
      - [ ] fallback: hash-only compare + “changed” marker
    - [ ] continue
  - [ ] ensure truncation rule (if any) is deterministic
- [ ] continue

### 2.5 Implement raw mode (nucleus compare)
- [ ] if `--kind raw|both`:
  - [ ] compare `logs/raw/**/*.sha256` (sorted)
  - [ ] if missing required sha256 files -> error (2) -> STOP
  - [ ] compute added/removed/changed -> include in output
- [ ] else:
  - [ ] continue

### 2.6 Log normalization (portable only; raw untouched)
Target: `internal/reviewpack/utils.go` (or wherever `createPortableLog()` is)
- [ ] Apply deterministic normalization:
  - [ ] replace duration patterns -> `<DURATION>`
  - [ ] replace cache markers -> `<CACHED>`
  - [ ] keep path redactions stable (tmpdir/repo-root)
- [ ] if normalization changes raw logs -> error "raw must remain truth" -> STOP

---

## 3) Tests (false-negative防止 + determinism)
File: `internal/reviewpack/diff_test.go`

- [ ] Add/confirm tests:
  - [ ] if portable dir missing -> exit 2
  - [ ] if same input twice -> same output (byte-identical)
  - [ ] if portable change -> exit 1
  - [ ] if raw sha256 change -> exit 1 (raw mode)
- [ ] if tests rely on timestamps/unstable paths:
  - [ ] normalize test fixtures
  - [ ] continue
- [ ] Run: `make ci-test`
- [ ] if fail -> error "tests failed" -> STOP

---

## 4) Proof: Bundle-to-Bundle Demonstration (reality check)
Goal: bundle `src_snapshot/` contains updated diff implementation.

- [ ] Ensure clean git:
  - [ ] if dirty -> error -> STOP
- [ ] Generate bundle A (using the repo’s pack path)
- [ ] Introduce controlled change:
  - [ ] if change touches raw -> avoid (portable-focused change)
  - [ ] else continue
- [ ] Commit controlled change (so pack preflight passes)
- [ ] Generate bundle B
- [ ] Run diff:
  - [ ] `go run cmd/reviewpack/main.go diff --kind portable --format text <A> <B>` -> expect exit 1
  - [ ] `go run cmd/reviewpack/main.go diff --kind raw --format text <A> <B>` -> expect exit 0 or 1 depending on what changed
  - [ ] if exit code violates contract -> error -> STOP

- [ ] Validate bundle reality:
  - [ ] extract bundle B and check:
    - [ ] `src_snapshot/internal/reviewpack/diff.go` contains new flags/exit/raw logic
  - [ ] if not -> error "bundle snapshot is old code" -> STOP

---

## 5) Docs & Walkthrough (no lies)
- [ ] Update walkthrough with:
  - [ ] exact commands used (bash blocks)
  - [ ] no `file://`
  - [ ] no `carousel` blocks
  - [ ] record bundle sha256 + diff summary
- [ ] if walkthrough claims features not present -> error "walkthrough mismatch" -> STOP

---

## 6) Final Gates (PR前最終)
- [ ] `make ci-test` PASS
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only` PASS
- [ ] Gate Checks (Step 1) PASS
- [ ] break -> proceed to PR commands

---

## 7) PR Commands (only after all gates pass)
- [ ] `git status -sb`
- [ ] `git diff --stat`
- [ ] `git add -A`
- [ ] Commit split rule:
  - [ ] if docs+code+tests all mixed heavily -> split commits (continue after split)
- [ ] `git push -u origin "$(git rev-parse --abbrev-ref HEAD)"`
- [ ] `gh pr create --fill`
