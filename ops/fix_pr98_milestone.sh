#!/bin/bash
# ops/fix_pr98_milestone.sh
# Fixes milestone for PR #98

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
STOP="0"

if [ -z "$ROOT" ]; then
  echo "ERROR: not in repo"
  STOP="1"
else
  cd "$ROOT" 2>/dev/null || true
  echo "OK: repo=$ROOT"
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OBS=".local/obs/s22-15_fix_milestone_${TS}"
mkdir -p "$OBS" 2>/dev/null || true
echo "OK: obs_dir=$OBS"

REPO="mt4110/maakie-brainlab"
PR="98"
MILE="S22-15"

CUR_MS=""
if [ "$STOP" = "0" ]; then
  CUR_MS="$(gh pr view "$PR" -R "$REPO" --json milestone -q '.milestone.title // ""' 2>/dev/null || true)"
  if [ -n "$CUR_MS" ]; then
    echo "OK: current_pr_milestone=$CUR_MS" | tee "$OBS/10_current.txt" || true
  else
    echo "WARN: current_pr_milestone_missing" | tee "$OBS/10_current.txt" || true
  fi
fi

# 1) Try gh pr edit
if [ "$STOP" = "0" ] && [ -z "$CUR_MS" ]; then
  echo "OK: try gh pr edit --milestone" | tee "$OBS/20_try_edit.txt" || true
  gh pr edit "$PR" -R "$REPO" --milestone "$MILE" 2>&1 | tee "$OBS/21_pr_edit.log" || true

  CUR_MS="$(gh pr view "$PR" -R "$REPO" --json milestone -q '.milestone.title // ""' 2>/dev/null || true)"
  if [ -n "$CUR_MS" ]; then
    echo "OK: milestone_set_via_pr_edit=$CUR_MS" | tee "$OBS/22_after_edit.txt" || true
  else
    echo "WARN: still_missing_after_pr_edit" | tee "$OBS/22_after_edit.txt" || true
  fi
fi

# 2) Fallback via gh api
if [ "$STOP" = "0" ] && [ -z "$CUR_MS" ]; then
  echo "OK: fallback via gh api (issues.update)" | tee "$OBS/30_fallback.txt" || true

  MNUM=""
  MNUM="$(gh api "repos/$REPO/milestones?state=open&per_page=100" --jq '.[] | select(.title=="S22-15") | .number' 2>/dev/null | head -n 1 || true)"
  if [ -z "$MNUM" ]; then
    MNUM="$(gh api "repos/$REPO/milestones?state=open&per_page=100" --jq '.[] | select(.title|startswith("S22")) | .number' 2>/dev/null | head -n 1 || true)"
  fi

  if [ -z "$MNUM" ]; then
    echo "ERROR: cannot find milestone number for S22-15 (or prefix S22)" | tee "$OBS/31_mnum_error.txt" || true
    STOP="1"
  else
    echo "OK: milestone_number=$MNUM" | tee "$OBS/31_mnum.txt" || true
    gh api -X PATCH "repos/$REPO/issues/$PR" -f milestone="$MNUM" 2>&1 | tee "$OBS/32_patch_issue.log" || true

    CUR_MS="$(gh pr view "$PR" -R "$REPO" --json milestone -q '.milestone.title // ""' 2>/dev/null || true)"
    if [ -n "$CUR_MS" ]; then
      echo "OK: milestone_set_via_api=$CUR_MS" | tee "$OBS/33_after_api.txt" || true
    else
      echo "ERROR: milestone_still_missing_after_api" | tee "$OBS/33_after_api.txt" || true
      STOP="1"
    fi
  fi
fi

if [ "$STOP" = "0" ]; then
  gh pr checks "$PR" -R "$REPO" 2>&1 | tee "$OBS/40_checks.log" || true
fi

echo "OK: done stop=$STOP"
