# S9 Plan — Pack Diff / Audit Comparability (Refinement “実体化”)
Last updated: 2026-02-13 (JST)

## 0) Intent
S9の「比較可能な監査」を完成させる。
“動く”ではなく **監査ツールとして嘘をつかない**ことが目的。

## 1) Core Contract (Must)
- portable-first（比較はportableを第一選択）
- audit truth is raw（portableは表示/比較ビュー）
- exit codes are strict:
  - 0 = no diff
  - 1 = diff found
  - 2 = error
- CLI flags:
  - `diff --kind=portable|raw|both` (default portable)
  - `diff --format=text|json` (default text)
- Safety:
  - WalkDir/ReadFile/Hash の err を握りつぶさない（false-negative禁止）
  - `log.Fatal` / `os.Exit` を diffロジック内で使わない（契約が崩れる）

## 2) Control-DSL (Plan notation)
This project uses a tiny control DSL to prevent “AI drift”:

- if CONDITION -> ACTION
- else if CONDITION -> ACTION
- else -> ACTION
- for EACH -> DO
- continue: proceed to next step
- break: stop loop and go to next phase
- skip: allowed only if “理由”を記録し、監査性を落とさない
- error: immediate failure (exit 2)
- STOP: do not proceed until fixed

## 3) Gate Before PR (Non-negotiable)
if any check fails -> error -> STOP

- G1: docs hygiene
  - No `file://` in docs/walkthrough
  - No weird md blocks like ````carousel
- G2: CLI wiring exists
  - `go run ... diff --help` shows `--kind` and `--format`
- G3: Exit code contract works (0/1/2)
- G4: verify-only PASS unchanged
- G5: Bundle `src_snapshot/` includes the “new diff implementation”
  - bundle is the proof of reality

## 4) Implementation Boundaries (What to diff)
Comparable Set:
- portable:
  - `logs/portable/**`
  - normalize noisy tokens: duration/cached paths etc (portable only)
- raw:
  - compare `logs/raw/**/*.sha256` (nucleus comparison)
  - missing guard in raw mode is error (exit 2)

Determinism rules:
- path ordering: lexicographic with slash paths
- newline normalization: `\n`
- output ordering: summary -> per-file detail
- truncation (if any): fixed rule and deterministic

## 5) Target Files (fixed paths)
Code:
- `internal/reviewpack/diff.go`
- `internal/reviewpack/diff_test.go`
- `internal/reviewpack/app.go` and/or `internal/reviewpack/flags.go` (CLI wiring)
Docs:
- `docs/reviewpack/WALKTHROUGH.md` (or `docs/reviewpack/WALKTHROUGH_S9.md`)
- `docs/ops/S9_PLAN.md`
- `docs/ops/S9_TASK.md`

## 6) Acceptance Criteria
- `make ci-test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS
- `go run cmd/reviewpack/main.go diff --help` includes `--kind/--format`
- `diff` exit code contract (0/1/2) validated
- docs hygiene (file:// and carousel blocks are zero)
- bundle generated after changes contains updated `src_snapshot/internal/reviewpack/diff.go`
