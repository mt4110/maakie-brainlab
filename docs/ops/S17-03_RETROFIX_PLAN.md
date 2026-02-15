# PLAN: S17-03 RETROFIX Audit Consistency
Status: IN_PROGRESS
Owner: ambi
Progress: 0%

## Goal
PR #51（S17-03）の 証拠・参照・集計を完全整合させ、監査的に「矛盾ゼロ」にする。

## Non-Goals
- 機能追加の拡張（run_alwaysの本筋改変、仕様変更の追加）はしない
- ※ただし **観測ログの透明化（SMOKE宣言）**は“契約強化”なのでOK。

## Invariants
- docs内の bundle名 / SHA256 / run id / 参照ファイルが 相互一致していること
- fix_evidence.txt が 空でないこと（最低限：根拠リンクとコマンド/出力の要約）
- PR本文に出す文章から [FILE_URI] を排除する（repo相対へ）

## Plan Pseudocode
### P0: Safety Snapshot
- repo_root := `git rev-parse --show-toplevel`
- branch := `git rev-parse --abbrev-ref HEAD`
- if branch == "main": error("do not work on main")
- if `git status --porcelain` not empty: error("dirty tree")
- head_sha := `git rev-parse --short HEAD`
- log("HEAD", head_sha)

### P1: Define Canonical Artifact (Definitive)
- canonical_bundle := ".local/review-bundles/review_bundle_20260215_121251.tar.gz"
- canonical_sha := "03cc0575170393c7481c96452d9a0aae5feef7480901993c71ab7b0a89416fff"
- if file(canonical_bundle) missing:
    for dir in [".local/review-bundles", ".local"]:
        for f in ls -t dir/review_bundle_*.tar.gz:
            if sha256(f) == canonical_sha: canonical_bundle=f; break
        if found: break
    if not found: error("canonical bundle not found")
- if sha256(canonical_bundle) != canonical_sha: error("SHA mismatch")

### P2: Repair Evidence Files (No empty evidence)
- target := "docs/evidence/s17-03/fix_evidence.txt"
- if file(target) missing: error("missing fix_evidence")
- if size(target) < MIN_BYTES:
    write(target) with summary of failure -> fix -> success, run IDs, and canonical info.

### P3: Add PASS run artifacts (Offline-friendly)
- pass_log := "docs/evidence/s17-03/log_pass_22027976749.txt"
- pass_run := "docs/evidence/s17-03/run_22027976749.json"
- fetch via `gh run view`

### P4: Fix Docs References (S17-03_TASK + summary)
- Sync `docs/ops/S17-03_TASK.md` and `docs/evidence/s17-03/fix_summary.md` with canonical values.
- Replace `[FILE_URI]` and absolute paths with portable links.

### P5: Milestone Rollup Consistency
- set `docs/ops/S17_PLAN.md` and `docs/ops/S17_TASK.md` to `DONE` and `100%`.

### P6: Contract/Observation Hardening
- patch `ops/run_always_1h.sh` with `SIGNING_MODE` logging.

### P7: Gates
- `make test`, `verify-only` (verify 03cc...), `ops/run_always_1h.sh` (local simulate).
