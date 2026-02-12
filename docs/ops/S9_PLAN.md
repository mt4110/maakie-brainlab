# S9 Plan — Pack Diff / Audit Comparability

Last updated: 2026-02-13 (JST)

## 0. Status / Context

- PR #33 merged: strict CI + structured logs ✅
- Strict CI: `go test -count=1 -mod=readonly` (`make ci-test`) ✅
- Logs:
  - `logs/raw/` = audit truth
  - `logs/portable/` = comparable view (noise-resistant)
  - raw sha256 guard exists ✅
- verify-only PASS must remain ✅

## 1. Goal (S9)

Complete “comparable audit” by enabling **bundle-to-bundle diff**:

- Use raw sha256 as the nucleus for tamper/delta detection
- Use portable view as first-choice diff surface
- Reference raw only when needed for audit defensibility

## 2. Non-Goals

- Do NOT change verification semantics (verify-only must stay PASS)
- Do NOT redefine raw/portable meaning (S8 contract remains source of truth)
- Do NOT introduce network dependency

## 3. Hard Invariants

- Invariant-1: verify-only behavior unchanged
- Invariant-2: audit truth = raw; portable = view for display/diff
- Invariant-3: diff output is deterministic (stable ordering, stable paths)
- Invariant-4: any “missing contract” (e.g. portable absent) is a hard error, not a silent pass

## 4. Deliverable (What we ship)

### 4.1 CLI

Add a new command (example):

- `reviewpack diff <bundleA> <bundleB> [--kind portable|raw|both] [--format text|json] [--out <path>]`

Recommended default:

- `--kind portable` (portable-first)

- Exit code:
  - `0` = no difference
  - `1` = difference found
  - `2` = error (bad bundle, missing dirs, guard mismatch, etc.)

### 4.2 Diff Scope Spec (Boundary line = what is compared)

We define the “Comparable Set” as:

- Portable Comparable Set (default):
  - `logs/portable/**` (all files, recursive)

- Raw Comparable Set (nucleus; optional mode):
  - raw sha256 manifest/guard artifacts (whatever S8 uses)
  - plus derived hash list of `logs/raw/**` (excluding the guard files themselves)

Rules:

- portable is the primary diff surface
- raw is only consulted when:
  - `--kind raw|both` is requested, OR
  - portable differs AND user wants drill-down (manual step outside CLI is allowed)

### 4.3 Determinism Rules

- File enumeration is sorted lexicographically by **slash path** (use `/`, not OS separator)
- Text diff is line-based with `\n` normalization
- Output format is stable:
  - Summary first (counts)
  - Then per-file diffs in sorted order

## 5. Design Outline (Algorithm)

### 5.1 Extract

- Create temp dirs A/B
- Extract bundleA -> dirA, bundleB -> dirB

### 5.2 Validate

- Validate both bundles have required structure:
  - if `logs/portable/` missing: ERROR (portable mode cannot proceed)
  - if raw guard expected but missing in raw mode: ERROR
- Validate raw sha256 guard:
  - if guard check fails: ERROR (tamper or corruption)
  - Note: portable diff does NOT “trust” portable alone; it relies on prior S8 guard for audit truth

### 5.3 Compare (portable)

- Walk `logs/portable/**`:
  - build map(path -> bytes hash or bytes)
- Compute:
  - Added / Removed / Modified lists
- For modified text files:
  - compute unified diff (line-based)
  - optionally cap output (but keep deterministic: cap rule must be fixed)

### 5.4 Compare (raw)

- Compare raw hash list:
  - Added / Removed / Changed hashes

### 5.5 Emit Result

- Print summary + per-file detail
- Return exit code based on difference presence

## 6. Acceptance Criteria

- AC-1: `make ci-test` PASS
- AC-2: verify-only PASS unchanged (run the same verify-only command used in S8)
- AC-3: `reviewpack diff` works offline
- AC-4: Running diff twice produces byte-identical output for same inputs
- AC-5: portable-only diff reports meaningful changes with low noise
- AC-6: raw mode detects tamper/delta via sha256 (nucleus behavior)

## 7. File Plan (Target paths)

Docs:

- `docs/ops/S9_PLAN.md` (this file)
- `docs/ops/S9_TASK.md` (execution plan for Ambi)

(Optional spec split if needed, but default keep in Plan):

- `docs/ops/S9_SPEC_PACK_DIFF.md` (ONLY if Plan grows too big)

Code (proposed; adjust to repo conventions):

- `cmd/reviewpack/main.go` (wire `diff` subcommand)
- `internal/reviewpack/diff.go` (core algorithm)
- `internal/reviewpack/diff_test.go` (determinism + cases)
- (Optional) `internal/reviewpack/diffjson.go` (json output)

## 8. Stop Conditions (Safety)

- STOP if verify-only starts failing (S9 must not proceed until fixed)
- STOP if guard verification behavior is accidentally changed (rollback)
- STOP if diff output is nondeterministic (must fix ordering/normalization)
