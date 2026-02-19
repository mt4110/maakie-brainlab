# S22-01 TASK — P1 IL canonicalize determinism

## 0. Safety / Invariants (non-negotiable)
- [ ] No exit-style control:
  - [ ] No `exit`, `return 1`, `set -e`, `trap ... EXIT`
  - [ ] No `sys.exit`, `raise SystemExit`, `assert` in scripts
  - [ ] Report via stdout: OK / ERROR / SKIP
- [ ] Heavy work split:
  - [ ] verify-il
  - [ ] go test
  - [ ] reviewpack verify-only
  - run separately (avoid terminal overload)

## 1. STATUS update (minimal deterministic edit)
- [ ] Add S22-01 row to docs/ops/STATUS.md (ONLY needed fields)
  - [ ] Target section: NEXT (or ACTIVE if that’s your rule)
  - [ ] Next column: `1% (Kickoff: IL canonicalize determinism)`
  - [ ] Keep table order stable
- [ ] Commit: `docs(ops): add S22-01 status row (kickoff)`

## 2. Locate current canonicalization & contract
- [ ] Locate ILCanonicalizer single source:
  - [ ] `rg -n "class ILCanonicalizer|canonicalize\(" src scripts tests docs/il || true`
- [ ] Locate guard output file usage:
  - [ ] `rg -n "il\.canonical\.json" scripts src tests || true`
- [ ] Confirm contract rules already documented:
  - [ ] `rg -n "Key Order|Whitespace|Numbers|NaN|Infinity|null" docs/il/IL_CONTRACT_v1.md || true`
- [ ] Record findings in S22-01_PLAN.md (short bullet)

## 3. Canonicalization contract (docs)
- [ ] Update docs/il/IL_CONTRACT_v1.md:
  - [ ] Explicit JSON serialization settings (sort_keys / separators / ensure_ascii / allow_nan)
  - [ ] Explicit newline rule for file output
  - [ ] Explicit rule for forbidden NaN/Infinity/null
  - [ ] Explicit string handling policy (no implicit normalization unless specified)

## 4. Implement canonicalizer determinism (single source)
- [ ] Edit: `src/il_validator.py`
  - [ ] ILCanonicalizer.canonicalize uses fixed settings:
    - sort keys
    - fixed separators
    - ensure_ascii false
    - allow_nan false
  - [ ] Ensure returned bytes are stable UTF-8 bytes
  - [ ] Decide & implement -0.0 handling (normalize OR reject) and document it

## 5. Guard script: validate -> canonicalize (no artifacts on fail)
- [ ] Edit: `scripts/il_guard.py`
  - [ ] If validate FAIL:
    - [ ] print `ERROR: ...`
    - [ ] print `SKIP: canonical output (validate_fail)`
    - [ ] DO NOT write `il.canonical.json`
  - [ ] If validate PASS:
    - [ ] try canonicalize; on exception:
      - [ ] print `ERROR: canonicalize failed: ...`
      - [ ] print `SKIP: canonical output (canonicalize_fail)`
      - [ ] DO NOT write canonical files
    - [ ] on success:
      - [ ] write `il.canonical.json` (exactly one trailing newline)
      - [ ] (optional) write `il.canonical.sha256`
      - [ ] print `OK: wrote il.canonical.json`
  - [ ] Ensure script never `sys.exit` / `SystemExit` / `assert`

## 6. Tests (determinism + forbidden)
- [ ] Update/add tests in `tests/test_il_validator.py`:
  - [ ] Same object different key order -> canonical bytes identical
  - [ ] Non-ASCII key/value -> canonical bytes stable
  - [ ] NaN/Infinity -> ERROR path (validate or canonicalize must reject)
  - [ ] null -> ERROR path (validate must reject)
  - [ ] forbidden fields -> ERROR path
- [ ] Keep tests minimal (no property-test explosion)

## 7. Verification (split, observe-only)
- [ ] Run (and keep logs):
  - [ ] `make verify-il || true`
  - [ ] `go test ./... || true`
  - [ ] `go run cmd/reviewpack/main.go submit --mode verify-only || true`
- [ ] Confirm outputs by reading logs:
  - [ ] PASS lines exist
  - [ ] No unexpected ERROR lines

## 8. PR (Milestone: S22-01)
- [ ] Push branch
- [ ] Create PR with SOT/Evidence/Gates
- [ ] Attach Milestone `S22-01`
- [ ] Update STATUS progress to 99% when PR opens, 100% when merged
