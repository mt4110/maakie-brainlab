#!/usr/bin/env bash
# no exit / no set -e / no non-zero control
# prints OK/ERROR/SKIP and never blocks parent terminal

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"
STOP="0"
DO_MERGE="0"
PR_IN=""

for A in "$@"; do
  if [ "$A" = "--merge" ]; then
    DO_MERGE="1"
  else
    PR_IN="$A"
  fi
done

if [ -z "$REPO_DIR" ]; then
  echo "ERROR: not in a git repo"
  STOP="1"
else
  cd "$REPO_DIR" 2>/dev/null || STOP="1"
fi

if [ "$STOP" = "0" ]; then
  echo "OK: repo=$REPO_DIR"
fi

PR=""
if [ "$STOP" = "0" ]; then
  if [ -n "$PR_IN" ]; then
    PR="$PR_IN"
    echo "OK: pr=$PR (arg)"
  else
    PR="$(gh pr view --json number --jq '.number' 2>/dev/null || true)"
    if [ -n "$PR" ]; then
      echo "OK: pr=$PR (current branch)"
    else
      echo "ERROR: cannot resolve PR number (pass PR number or run in PR branch)"
      STOP="1"
    fi
  fi
fi

NAME=""
SHA=""
if [ "$STOP" = "0" ]; then
  NAME="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
  SHA="$(gh pr view "$PR" --json headRefOid --jq '.headRefOid' 2>/dev/null || true)"
  if [ -n "$NAME" ] && [ -n "$SHA" ]; then
    echo "OK: name=$NAME sha=$SHA"
  else
    echo "ERROR: cannot resolve repo/sha (gh auth?)"
    STOP="1"
  fi
fi

MILESTONE=""
if [ "$STOP" = "0" ]; then
  MILESTONE="$(gh api -H "Accept: application/vnd.github+json" "repos/$NAME/pulls/$PR" \
    --jq '.milestone.title // ""' 2>/dev/null || true)"
  if [ -n "$MILESTONE" ]; then
    echo "OK: milestone=$MILESTONE"
  else
    echo "WARN: milestone missing, attempting autofix"
    # --- S22-11 milestone autofix (zero-thought) ---
    HEAD_REF="$(gh pr view "$PR" --json headRefName --jq '.headRefName // ""' 2>/dev/null || true)"
    INF="$(printf "%s\n" "$HEAD_REF" | grep -o -i -E 's[0-9]{2}-[0-9]{2}' | head -1 || true)"
    if [ -z "$INF" ]; then
      echo "ERROR: cannot infer milestone from head_ref=$HEAD_REF"
      STOP="1"
    else
      WANT="$(printf "%s\n" "$INF" | sed 's/^s/S/' | tr '[:lower:]' '[:upper:]')"
      echo "OK: inferred milestone title=$WANT"
      MNUM="$(gh api "repos/$NAME/milestones?state=all&per_page=100" \
        --jq ".[] | select(.title==\"$WANT\") | .number" 2>/dev/null | head -1 || true)"
      if [ -z "$MNUM" ]; then
        echo "ERROR: milestone not found title=$WANT"
        STOP="1"
      else
        gh api -X PATCH "repos/$NAME/issues/$PR" -f milestone="$MNUM" 2>/dev/null >/dev/null || true
        echo "OK: milestone set number=$MNUM title=$WANT"
        MILESTONE="$(gh api -H "Accept: application/vnd.github+json" "repos/$NAME/pulls/$PR" \
          --jq '.milestone.title // ""' 2>/dev/null || true)"
        echo "OK: milestone(after)=$MILESTONE"
        if [ -z "$MILESTONE" ]; then
          echo "ERROR: milestone still missing after autofix"
          STOP="1"
        fi
      fi
    fi
    # --- /S22-11 milestone autofix ---
  fi
fi

# Must be success: milestone_required (prefer status; fallback check-runs)
MS_STATE=""
MS_CONCL=""
if [ "$STOP" = "0" ]; then
  # 1) Prefer commit status context (this repo posts statuses explicitly)
  MS_STATE="$(gh api -H "Accept: application/vnd.github+json" "repos/$NAME/commits/$SHA/status"     --jq '.statuses | map(select(.context=="milestone_required")) | .[0].state // ""' 2>/dev/null || true)"

  if [ "$MS_STATE" = "success" ]; then
    echo "OK: status milestone_required=success"
  elif [ -n "$MS_STATE" ]; then
    echo "ERROR: status milestone_required not success: state=${MS_STATE:-EMPTY}"
    STOP="1"
  else
    # 2) Fallback: scan check-runs (name is often job-name, not workflow-name)
    MS_CONCL="$(gh api -H "Accept: application/vnd.github+json" "repos/$NAME/commits/$SHA/check-runs"       --jq '[.check_runs[] | select(((.name // "") | test("milestone_required"; "i")) or ((.name // "") == "milestone"))] | .[0].conclusion // ""' 2>/dev/null || true)"

    if [ "$MS_CONCL" = "success" ]; then
      echo "OK: check_run milestone_required=success"
    elif [ -n "$MS_CONCL" ]; then
      echo "ERROR: check_run milestone_required not success: conclusion=${MS_CONCL:-EMPTY}"
      STOP="1"
    else
      echo "WARN: milestone_required not observable via status/check-runs (non-blocking); rely on milestone + global checks gate"
    fi
  fi
fi

# Block if any pending or failing check-runs exist
PENDING=""
FAILS=""
if [ "$STOP" = "0" ]; then
  PENDING="$(gh api -H "Accept: application/vnd.github+json" "repos/$NAME/commits/$SHA/check-runs" \
    --jq '[.check_runs[] | select(.status != "completed")] | length' 2>/dev/null || true)"
  FAILS="$(gh api -H "Accept: application/vnd.github+json" "repos/$NAME/commits/$SHA/check-runs" \
    --jq '[.check_runs[] | select(.status=="completed" and (.conclusion!="success" and .conclusion!="neutral" and .conclusion!="skipped"))] | length' 2>/dev/null || true)"

  echo "OK: check_runs pending=${PENDING:-UNKNOWN} failing=${FAILS:-UNKNOWN}"

  if [ -n "$PENDING" ] && [ "$PENDING" != "0" ]; then
    echo "ERROR: checks still running (block merge)"
    STOP="1"
  fi
  if [ -n "$FAILS" ] && [ "$FAILS" != "0" ]; then
    echo "ERROR: failing checks exist (block merge)"
    STOP="1"
  fi
fi

if [ "$STOP" = "0" ]; then
  if [ "$DO_MERGE" = "1" ]; then
    echo "OK: merging PR $PR"
    gh pr merge "$PR" --squash --delete-branch 2>/dev/null || true
    echo "OK: merge command executed (check GH UI for result)"
  else
    echo "OK: dry-run (pass --merge to execute)"
  fi
else
  echo "SKIP: merge not executed (see ERROR above)"
fi

true
