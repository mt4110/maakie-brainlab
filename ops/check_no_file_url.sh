#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${ROOT}" ]]; then
  echo "[FAIL] not a git repo. run inside repo." >&2
  exit 2
fi
cd "$ROOT"

echo "[CHECK] Scanning for forbidden file[:]// links..."

targets=()
[[ -d docs ]] && targets+=("docs")
[[ -d .github ]] && targets+=(".github")

# root-level markdown files
while IFS= read -r -d '' f; do
  targets+=("$f")
done < <(find . -maxdepth 1 -type f -name "*.md" -print0 2>/dev/null || true)

if (( ${#targets[@]} == 0 )); then
  echo "[FAIL] no scan targets found (docs/.github/*.md missing). Are you in repo root?" >&2
  exit 2
fi

echo "[INFO] targets:"
for t in "${targets[@]}"; do
  echo " - $t"
done

# Deny: link-style or raw file URLs (to prevent accidental clickables)
pattern='\]\(file[:]//|<file[:]//|file[:]///'

matches=()
for t in "${targets[@]}"; do
  if [[ -d "$t" ]]; then
    while IFS= read -r line; do matches+=("$line"); done < <(grep -R -n -E "$pattern" "$t" || true)
  else
    while IFS= read -r line; do matches+=("$line"); done < <(grep -n -E "$pattern" "$t" || true)
  fi
done

if (( ${#matches[@]} > 0 )); then
  echo "[FAIL] Forbidden file[:]// link(s) found:" >&2
  printf '%s\n' "${matches[@]}" >&2
  echo "next: remove link-style file[:]// and use repo-relative paths. See docs/ops/IF_FAIL_C10FIX04.md" >&2
  exit 1
fi

echo "[OK] No forbidden file[:]// links found."
