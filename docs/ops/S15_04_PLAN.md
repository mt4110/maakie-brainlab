# S15-04: Naive Scan Artifact Cleanup & Test Improvements

## Status (S15 series)
- S15-01 merged (#35): pack delta v1
- S15-02 merged (#36): mkdir error fail-fast
- S15-04 (this PR): cleanup naive scan artifacts + add fail-fast test coverage

## Summary
This PR completes specific improvements identified during S15-02 review:
1. Stop writing naive secrets/null-byte scan artifacts to disk (log instead)
2. Add subprocess test to verify reviewpack fail-fast behavior on mkdir errors
3. Fix MkdirTemp error message in verify.go to show pattern, not empty tmpDir

## Changes Made

### 1. Naive Scan Artifact Cleanup (evidence.go)
- **Before**: `scanSecrets()` wrote `21_secrets_scan.log`, `scanNull()` wrote `20_null_bytes.txt`
- **After**: scanSecrets() uses `fmt.Printf()` and scanNull() uses `fmt.Println()` instead
- **Rationale**: These naive scans were informational only and cluttering the artifact directory

### 2. Test Coverage for Fail-Fast (mkdir_fail_fast_test.go)
- Added `TestMkdirFailFastSubprocess` using subprocess/helper pattern
- Verifies reviewpack actually calls `log.Fatalf` and exits with code 1 on mkdir failure
- Tests that error message includes the blocking path
- **Rationale**: Previous tests validated OS behavior; this validates our code's fail-fast behavior

### 3. Diagnostics Improvement (verify.go)
- Fixed `log.Fatalf(msgFatalMkdirTemp, tmpDir, err)` → `log.Fatalf(msgFatalMkdirTemp, "reviewpack-verify-*", err)`
- **Rationale**: tmpDir is empty string when MkdirTemp fails; show the pattern instead for better diagnostics

## Out of Scope
This PR does NOT include:
- Comprehensive log.Fatalf path audit across all files (separate effort)
- Removing `_ = os.WriteFile(` calls (already clean per grep)
- Large-scale error handling refactoring

## Evidence
```bash
# No ignored WriteFile calls remain:
grep -n "_ = os\.WriteFile\(" internal/reviewpack/*.go
# (returns nothing)

# Tests pass:
make test
```
