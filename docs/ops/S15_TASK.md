# S15 Task List

S15-H00 Preflight

- [x] if git status --porcelain=v1 is dirty -> STOP
- [x] if branch is not "s15-00-pack-delta-v1" -> STOP

S15-H01 Verify Workflow path

- [x] find .github/workflows/verify_pack.yml uniquely
- [x] if multiple found -> STOP

S15-H03 BASE_DIR Hardening (Audit Quality)

- [x] set BASE_DIR to "${{ runner.temp }}/main-worktree"
- [x] add git worktree remove/prune before and after use
- [x] if git fetch origin main fails -> exit 2 (pack_delta\t2) -> STOP
- [x] if git worktree add fails -> exit 2 (pack_delta\t2) -> STOP

S15-H04 Summary Bug Fix

- [x] write delta summary to ".local/ci/pack_delta/summary.md"
- [x] append to main summary in CI Summary step
- [x] if main summary overwritten -> STOP

S15-H05 Baseline Prep

- [x] seed eval/results/ci.jsonl in BASE_DIR before submit
- [x] if seed fails -> STOP
- [x] if bundle count in PR or MAIN is not exactly 1 (ambiguity) -> exit 2 (pack_delta\t2) -> STOP

S15-H06 Doc Hygiene

- [x] if rg "file:///" has hits in docs/ -> STOP
- [x] replace absolute paths with relative repo paths

S15-H08 Contract Gate

- [x] if diff --help missing --kind/--format -> STOP

S15-H09 Local Gate

- [x] if make ci-test fails -> STOP
- [x] if submit --mode verify-only fails -> STOP

S15-H10 SOT Alignment

- [x] if docs/ops/S15_* doesn't match implementation -> STOP
- [x] if Makefile changed without justification in S15_PLAN -> STOP
