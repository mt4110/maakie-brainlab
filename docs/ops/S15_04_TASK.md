# S15-04 TASK: Naive Scan Artifact Cleanup & Test Improvements

## Completed Changes

### 1. Remove Naive Scan Artifact Files
- [x] Update `scanSecrets()` in evidence.go to use fmt.Printf instead of log.Printf
- [x] Update `scanNull()` in evidence.go to use log.Printf instead of WriteFile
- [x] Verify no `_ = os.WriteFile(` calls remain in product code

### 2. Add Subprocess Test for Fail-Fast Behavior  
- [x] Create mkdir_fail_fast_test.go with subprocess/helper pattern
- [x] Test verifies reviewpack exits with code 1 on mkdir failure
- [x] Test verifies error message includes the blocking path
- [x] Run tests to ensure they pass

### 3. Fix Diagnostics in verify.go
- [x] Update MkdirTemp error message to show pattern instead of empty tmpDir variable
- [x] Ensure error messages are helpful for debugging

## Evidence
```bash
# Verify no ignored WriteFile calls:
grep -n "_ = os\.WriteFile\(" internal/reviewpack/*.go

# Run tests:
make test
```

## Notes
This PR focuses on three specific improvements rather than comprehensive diagnostics work.
Future work may include broader log.Fatalf message improvements across all files.
