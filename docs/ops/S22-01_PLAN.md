# S22-01 PLAN — P1 IL canonicalize determinism (bytes stable across env)

## Goal
- Same IL input (semantically identical) -> same canonical bytes ALWAYS.
- Canonical bytes becomes the foundation for:
  - diff (stable)
  - signature (stable)
  - evaluation artifact identity (stable)

## Non-Goal (explicit)
- Do NOT design IL executor here (that is S22-02).
- Do NOT introduce new IL semantics.
- Do NOT produce canonical artifacts when validation fails.

## Scope (Source of Truth)
- Canonicalizer single-source-of-truth:
  - src/il_validator.py : ILValidator + ILCanonicalizer
- Guard behavior:
  - scripts/il_guard.py validates first
  - ONLY when validate PASS -> write artifacts:
    - il.canonical.json (newline-terminated)
    - (optional but recommended) il.canonical.sha256

## Determinism Contract (must be documented)
- Key order: MUST be stable (sorted)
- Whitespace: MUST be fixed (no pretty print)
- Encoding: UTF-8
- Numbers:
  - MUST NOT: NaN / Infinity
  - MUST define handling of -0.0 (normalize to 0.0 OR forbid; pick one and test)
- null:
  - MUST NOT use null; optionals are expressed by missing fields
- Strings:
  - preserve code points as-is (no implicit normalization) unless contract explicitly says otherwise

## Canonicalization Algorithm (working theory, minimal & stable)
- Precondition: data is already validated by ILValidator.
- Serialize with fixed JSON settings:
  - sort keys = true
  - separators = (",", ":")  # no spaces
  - ensure_ascii = false     # keep UTF-8 chars (stable bytes)
  - allow_nan = false        # rejects NaN/Infinity via exception (must be caught by caller)
- Output:
  - canonical bytes = UTF-8 bytes of the JSON text
  - file output adds exactly one trailing "\n" for diff ergonomics

## Failure Semantics (no lies)
- validate FAIL:
  - print "ERROR: ..." and "SKIP: canonical output (reason=validate_fail)"
  - do not write il.canonical.json
- validate PASS but canonicalize throws:
  - print "ERROR: canonicalize failed: <summary>"
  - do not write il.canonical.json
- Always:
  - scripts must NOT sys.exit / raise SystemExit / assert
  - report via text: OK / ERROR / SKIP

## Pseudocode (branching & stop conditions)

```python
if repo not clean enough to proceed:
    print("ERROR: ..."); stop_flag = 1

# main flow

# read IL -> sanitized
errors = validate(sanitized)
if errors:
    print("ERROR: validation failed")
    print("SKIP: canonical artifacts (validate_fail)")
    # continue (do not produce artifacts)

try:
    b = canonicalize(sanitized)
except Exception as e:
    print("ERROR: canonicalize failed")
    print("SKIP: canonical artifacts (canonicalize_fail)")
    # continue

write il.canonical.json = b + "\n"
write il.canonical.sha256 = sha256(b) + "\n"
print("OK: canonical artifacts written")
```

## DoD (Definition of Done)
- ILCanonicalizer is the only canonical bytes generator (no duplicates elsewhere).
- scripts/il_guard.py:
  - validate PASS -> writes canonical artifacts
  - validate FAIL -> writes none, prints explicit SKIP
- Tests:
  - key order variance -> canonical bytes identical
  - forbidden: NaN/Infinity -> ERROR path
  - forbidden: null -> ERROR path
  - non-ASCII keys/values -> stable canonical bytes
  - forbidden fields -> ERROR path
- Docs:
  - docs/il/IL_CONTRACT_v1.md (or dedicated canonical section) explicitly states serialization settings.

## Progress (for STATUS)
- kickoff: 1%
- implemented + tests green: 90%
- PR open + CI green: 99%
- merged: 100%
