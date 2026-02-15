# PLAN: S17-03 RETROFIX Audit Consistency
Status: DONE
Owner: ambi
Progress: 100%

## Goal
PR #51（S17-03）の 証拠・参照・集計を完全整合させ、監査的に「矛盾ゼロ」にする。

## Non-Goals
- 機能追加の拡張（run_alwaysの本筋改変、仕様変更の追加）はしない
- ※ただし **観測ログの透明化（SMOKE宣言）**は“契約強化”なのでOK。

## Invariants
- docs内の bundle名 / SHA256 / run id / 参照ファイルが 相互一致していること
- fix_evidence.txt が 空でないこと（最低限：根拠リンクとコマンド/出力の要約）
- PR本文に出す文章から file:// を排除する（repo相対へ）

## Plan Pseudocode
### P0: Safety Snapshot
- repo_root := `git rev-parse --show-toplevel`
- git status -sb (Check: clean)

### P1: Canonical Fixation (03cc / 121251)
- **Canonical Definition**: `review_bundle_20260215_121251.tar.gz` / `03cc0575...416fff`
- Update all references in `docs/ops/S17-03_TASK.md`, `fix_summary.md`, and `fix_evidence.txt` to align with this canonical bundle.

### P2: Documentation Completion
- Set `docs/ops/S17-03_RETROFIX_PLAN.md` to `DONE` / `100%`.
- Set `docs/ops/S17-03_RETROFIX_TASK.md` to `DONE` / `100%`.

### P3: Consistency Gate (Drift Prevention)
- `rg -n "eb8631|124326" docs/ops docs/evidence` must return 0 hits.
- `rg -n "Status: IN_PROGRESS|Progress: 0%" docs/ops/S17-03*` must return 0 hits.

### P4: Final Ritual
- `make test`, `verify-only` (ensure CLEAN).
- Commit & Push.
- Update PR #51 body with canonical `03cc...` ritual.
