
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

Recovery: accidental commit on main (local only)
git switch -c fix/rescue-main-commit
git push -u origin HEAD

git switch main
git fetch origin
git reset --hard origin/main


