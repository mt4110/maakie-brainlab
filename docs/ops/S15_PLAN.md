# S15: Pack Delta CI Report (V1)

## Goal

Enable automatic visualization of bundle differences between the current PR and the `main` baseline in CI.
This provides immediate feedback on what changed in the submission bundle.

## Design

1. **Baseline Generation**: Fetch `origin/main` and generate a bundle using `git worktree` at
   `${{ runner.temp }}/main-worktree`. This ensures isolation from the PR workspace and avoids
   accidental artifact inclusion.
2. **Comparison**: Use `reviewpack diff` to compare the PR bundle against the baseline.
3. **Report**: Output both JSON and Text formats. JSON is used for strict exit code handling (EC=2 is failure),
   while Text is for human readability in the CI summary.
4. **Integration**: Inject the delta reporting steps into the `Verify Pack` workflow.
5. **Summary**: The delta report is written to `.local/ci/pack_delta/summary.md` and appended to the
   main CI summary to prevent overwrites.
6. **Audit Quality Hardening**:
   - Explicitly checks for `git fetch` failure.
   - Strictly enforces a "one-bundle-only" rule to prevent ambiguity in comparison.
   - Any violation of these checks results in a system error (EC=2), recorded in `pack_delta`.

## Exit Code Contract

- `0`: No diff (Success)
- `1`: Diff found (Success, informational)
- `2`: System error (Failure)
