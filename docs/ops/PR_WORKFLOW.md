
PR workflow (safe + reproducible)
Golden rule

Do not push commits directly to main.

Always create a branch first, then open a PR.

## AI Requests (Strict Guard)

### Enable Local Hooks (One-time setup)
`git config core.hooksPath .githooks`

### Workflow
When asking AI to write code or docs:
1.  **Copy & Paste**: The "AI Constitution Block" from `docs/rules/AI_TEXT_GUARD.md` must be at the top of your prompt.
2.  **Self-Check**: The pre-commit hook will also catch this, but checking manually saves time.
    `bash ops/finalize_clean.sh --check`
3.  **Guard-Safe**: Ensure no forbidden patterns (file URLs) exist in the output.
4.  **Verify**: Always run `nix run .#prverify` before pushing.

Standard flow
git switch main
git pull --ff-only
git switch -c <branch>

# work, commit...
git push -u origin HEAD

gh pr create \
  --base main \
  --head "$(git branch --show-current)" \
  --title "<TITLE>" \
  --body-file .local/pr-templates/<PR>.md

Create a PR body from template
mkdir -p .local/pr-templates
cp docs/pr_templates/s5.md .local/pr-templates/<PR>.md
# edit .local/pr-templates/<PR>.md


## Milestone discipline (S20-10)

Purpose: prevent “PR has no milestone” accidents by detection, not by blocking dev flow.

Policy:
- Default: PR should have a milestone.
- Exception: if label `no-milestone-ok` is present, milestone check is skipped (PASS).
- Draft PR: skipped (PASS).

CI:
- A workflow posts a commit status with context `milestone_required`.
- Missing milestone (and no exception label, non-draft) => status `failure`.
- **Invariant**: Every decision must be written in PR body.
- **Rule**: Milestone OR (no-milestone-ok + **Non-empty Reason**)

Note:
- `milestone_advisory` is success-only (WARN is non-blocking) and never blocks merges.
- `milestone_required` is detection-focused; do NOT add it to required checks by default.

## Milestone hygiene (rerun罠の根絶)

- Milestone を後付け/外ししたときは、`pull_request` の `milestoned` / `demilestoned` で自動再判定される。
- GitHub Actions の `gh run rerun` は、過去の `pull_request` event payload（化石）を再生することがある。
  - そのため判定ロジックは event payload に依存しない。
- 判定は GitHub API を用いて「現在のPR状態（真実）」を取得して行う（truth over payload）。

Recovery: accidental commit on main (local only)
git switch -c fix/rescue-main-commit
git push -u origin HEAD

git switch main
git fetch origin
git reset --hard origin/main


## Milestone Autofill & Merge Guard (S21-04)

- Milestone は `milestone_autofill` が自動付与する（Sxx推測）
- マージは `ops/pr_merge_guard.sh` 経由（UI mergeは運用禁止）

## Merge Guard Contract (S22-17)

- `ops/pr_merge_guard.sh` の blocking 条件は required checks と check-runs のみ。
- milestone 系は観測 + 自動補正（best-effort）で、判定は non-blocking。
- `milestone_required` の失敗は WARN 扱い（merge停止条件にしない）。
- 実行マージは merge-commit 固定（`gh pr merge --merge --match-head-commit <sha>`）。
