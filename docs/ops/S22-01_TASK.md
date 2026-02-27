# S22-01 TASK — P1 IL canonicalize determinism

## 0. Safety / Invariants (non-negotiable)
- [x] No exit-style control:
  - [x] No `exit`, `return 1`, `set -e`, `trap ... EXIT`
  - [x] No `sys.exit`, `raise SystemExit`, `assert` in scripts
  - [x] Report via stdout: OK / ERROR / SKIP
- [x] Heavy work split:
  - [x] verify-il
  - [x] go test
  - [x] reviewpack verify-only
  - run separately (avoid terminal overload)

## 1. STATUS update (minimal deterministic edit)
- [x] Add S22-01 row to docs/ops/STATUS.md (ONLY needed fields)
  - [x] Target section: NEXT (or ACTIVE if that’s your rule)
  - [x] Next column: `1% (Kickoff: IL canonicalize determinism)`
  - [x] Keep table order stable
- [x] Commit: `docs(ops): add S22-01 status row (kickoff)`

## 2. Locate current canonicalization & contract
- [x] Locate ILCanonicalizer single source:
  - [x] `rg -n "class ILCanonicalizer|canonicalize\(" src scripts tests docs/il || true`
- [x] Locate guard output file usage:
  - [x] `rg -n "il\.canonical\.json" scripts src tests || true`
- [x] Confirm contract rules already documented:
  - [x] `rg -n "Key Order|Whitespace|Numbers|NaN|Infinity|null" docs/il/IL_CONTRACT_v1.md || true`
- [x] Record findings in S22-01_PLAN.md (short bullet)

## 3. Canonicalization contract (docs)
- [x] Update docs/il/IL_CONTRACT_v1.md:
  - [x] Explicit JSON serialization settings (sort_keys / separators / ensure_ascii / allow_nan)
  - [x] Explicit newline rule for file output
  - [x] Explicit rule for forbidden NaN/Infinity/null
  - [x] Explicit string handling policy (no implicit normalization unless specified)

## 4. Implement canonicalizer determinism (single source)
- [x] Edit: `src/il_validator.py`
  - [x] ILCanonicalizer.canonicalize uses fixed settings:
    - sort keys
    - fixed separators
    - ensure_ascii false
    - allow_nan false
  - [x] Ensure returned bytes are stable UTF-8 bytes
  - [x] Decide & implement -0.0 handling (normalize OR reject) and document it

## 5. Guard script: validate -> canonicalize (no artifacts on fail)
- [x] Edit: `scripts/il_guard.py`
  - [x] If validate FAIL:
    - [x] print `ERROR: ...`
    - [x] print `SKIP: canonical output (validate_fail)`
    - [x] DO NOT write `il.canonical.json`
  - [x] If validate PASS:
    - [x] try canonicalize; on exception:
      - [x] print `ERROR: canonicalize failed: ...`
      - [x] print `SKIP: canonical output (canonicalize_fail)`
      - [x] DO NOT write canonical files
    - [x] on success:
      - [x] write `il.canonical.json` (exactly one trailing newline)
      - [x] (optional) write `il.canonical.sha256`
      - [x] print `OK: wrote il.canonical.json`
  - [x] Ensure script never `sys.exit` / `SystemExit` / `assert`

## 6. Tests (determinism + forbidden)
- [x] Update/add tests in `tests/test_il_validator.py`:
  - [x] Same object different key order -> canonical bytes identical
  - [x] Non-ASCII key/value -> canonical bytes stable
  - [x] NaN/Infinity -> ERROR path (validate or canonicalize must reject)
  - [x] null -> ERROR path (validate must reject)
  - [x] forbidden fields -> ERROR path
- [x] Keep tests minimal (no property-test explosion)

## 7. Verification (split, observe-only)
- [x] Run (and keep logs):
  - [x] `make verify-il || true`
  - [x] `go test ./... || true`
  - [x] `go run cmd/reviewpack/main.go submit --mode verify-only || true`
- [x] Confirm outputs by reading logs:
  - [x] PASS lines exist
  - [x] No unexpected ERROR lines

## 8. PR (Milestone: S22-01)
- [x] Push branch
- [x] Create PR with SOT/Evidence/Gates
- [x] Attach Milestone `S22-01`
- [x] Update STATUS progress to 99% when PR opens, 100% when merged
