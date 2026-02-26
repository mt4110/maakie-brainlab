#!/usr/bin/env bash

# Branch name guard (problem-pattern limited).
# Policy: only forbid codex/feat* family.

branch="${1:-}"
if [ -z "$branch" ]; then
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi

if [ -z "$branch" ]; then
  echo "ERROR: cannot resolve branch name"
  exit 2
fi

if [ "$branch" = "HEAD" ]; then
  echo "SKIP: detached HEAD"
  exit 0
fi

if echo "$branch" | grep -Eq '^codex/feat([/-]|$)'; then
  echo "ERROR: forbidden branch pattern detected: $branch"
  echo "ERROR: do not continue on this branch"
  echo "OK: recreate branch from same HEAD, e.g. git switch -c feat/<slug>"
  exit 1
fi

echo "OK: branch-name-guard passed ($branch)"
exit 0
