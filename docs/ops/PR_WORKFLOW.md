
PR workflow (safe + reproducible)
Golden rule

Do not push commits directly to main.

Always create a branch first, then open a PR.

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

Recovery: accidental commit on main (local only)
git switch -c fix/rescue-main-commit
git push -u origin HEAD

git switch main
git fetch origin
git reset --hard origin/main


