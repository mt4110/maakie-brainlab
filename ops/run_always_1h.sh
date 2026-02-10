#!/bin/bash
# ops/run_always_1h.sh
# mimic CI "Run Always" workflow locally

set -u

# Failure Injection (env var: INJECT_FAILURE)
INJECT_FAILURE="${INJECT_FAILURE:-none}"

# 1. Preflight (Auto-Stash)
mkdir -p .local/ci
echo "== Preflight (Local) ==" | tee .local/ci/00_preflight.log

stash_created="0"
stash_before_cnt="$(git stash list | wc -l | tr -d ' ')"
git_status="$(git status --porcelain=v1 || true)"

if [ -z "$git_status" ]; then
  echo "[OK] working tree clean" | tee -a .local/ci/00_preflight.log
else
  echo "[WARN] working tree dirty -> auto-stash (-u) so clean-required steps can run" | tee -a .local/ci/00_preflight.log
  echo "$git_status" | tee -a .local/ci/00_preflight.log

  # -u: untrackedも退避（ただし ignored は退避しない）
  git stash push -u -m "run_always_1h:auto-stash $(date -u +%Y%m%dT%H%M%SZ)" >/dev/null 2>&1 || true

  stash_after_cnt="$(git stash list | wc -l | tr -d ' ')"
  if [ "$stash_after_cnt" -gt "$stash_before_cnt" ]; then
    stash_created="1"
    echo "[OK] stash created: stash@{0}" | tee -a .local/ci/00_preflight.log
  else
    echo "[INFO] no stash created" | tee -a .local/ci/00_preflight.log
  fi
fi

restore_stash() {
  # Injection restore
  if [ "${INJECT_FAILURE:-}" = "doclinks" ]; then
      echo "[INJECT] doclinks: restoring README.md" | tee -a ".local/ci/20_inject.log"
      git restore -- README.md 2>/dev/null || true
  fi

  # Stash restore
  if [ "$stash_created" = "1" ]; then
    echo "[INFO] restoring stash stash@{0}" | tee -a .local/ci/00_preflight.log
    git stash pop stash@{0} >/dev/null 2>&1 || {
      echo "[ERROR] stash pop failed; try apply and keep stash" | tee -a .local/ci/00_preflight.log
      git stash apply stash@{0} >/dev/null 2>&1 || true
    }
  fi
}
trap 'restore_stash' EXIT

# 2. Init CI logic
echo "== Init CI (Local) =="
date -u +"%Y%m%dT%H%M%SZ" > .local/ci/00_utc.txt
echo "sha=$(git rev-parse HEAD)" > .local/ci/00_meta.txt
echo "run_id=local-$(date +%s)" >> .local/ci/00_meta.txt
rm -f .local/ci/10_status.tsv

# 3. Key Steps (wrapped)

# Mimic CI Env (verify-only)
export S5_MODE="verify-only"
export GATE1_VERIFY_ONLY="1"
export S6_SIGNING_KEY="${S6_SIGNING_KEY:-}"
export S6_VERIFY_KEY="${S6_VERIFY_KEY:-}"

run_step() {
    local name="$1"
    shift
    echo "== Step: $name =="
    set +e
    (
        set -euo pipefail
        "$@"
    ) 2>&1 | tee ".local/ci/${name}.log"
    local ec=${PIPESTATUS[0]}
    echo -e "${name}\t${ec}" >> .local/ci/10_status.tsv
    return 0 # Always pass the wrapper
}

# 3.1 Seed
if [ "$INJECT_FAILURE" == "seed-missing" ]; then
    echo "[INJECT] seed-missing"
    # Do nothing or corrupt
else
    # Mimic CI seed
    run_step "seed_eval" bash ops/seed_eval_results.sh
fi

# 3.2 S5 Evidence Pack
run_step "s5_evidence_pack" make s5

# 3.3 Review Bundle
run_step "review_bundle" go run ./cmd/reviewpack/main.go submit --mode verify-only

# 3.4 Verify Evidence
run_step "verify_evidence" bash -c 'PACK=$(ls -t .local/reviewpack_artifacts/evidence_pack_*.tar.gz | head -n 1); make verify-pack PACK="$PACK"'

# 3.5 Verify Bundle
run_step "verify_bundle" bash -c 'PACK=$(ls -t review_bundle_*.tar.gz | head -n 1); make verify-pack PACK="$PACK"'

# 3.6 Doc Links

inject_doclinks_begin() {
  [ "${INJECT_FAILURE:-}" = "doclinks" ] || return 0
  echo "[INJECT] doclinks: patching README.md (tracked) for scan..." | tee -a ".local/ci/20_inject.log"
  # Inject multiple forbidden patterns to ensure detection (Obfuscated from linter)
  PROTO="file"
  PROTO="${PROTO}://"
  printf "\n<!-- INJECT_DOC_LINKS_BEGIN -->\n[file-url](${PROTO}/INJECT_DO_NOT_OPEN)\n${PROTO}/INJECT_DO_NOT_OPEN\n${PROTO}localhost/INJECT_DO_NOT_OPEN\n${PROTO}/INJECT_DO_NOT_OPEN\n<!-- INJECT_DOC_LINKS_END -->\n" >> README.md
  # Check if injection worked
  rg -n "INJECT_DO_NOT_OPEN|file://" README.md | tee -a ".local/ci/20_inject.log" || true
}

if [ "${INJECT_FAILURE:-}" = "doclinks" ]; then
  inject_doclinks_begin
fi

# Debug recipe
make -n check-doc-links > .local/ci/21_doclinks_recipe.txt 2>&1 || true

run_step "doc_links" make check-doc-links

# Fail Safe for Injection
if [ "$INJECT_FAILURE" = "doclinks" ]; then
  doc_ec="$(awk '$1=="doc_links"{print $2}' .local/ci/10_status.tsv | tail -n 1)"
  if [ "${doc_ec:-0}" = "0" ]; then
    echo "[INJECT][ERROR] doclinks injection did NOT trigger failure; marking doc_links as invalid test (ec=99)" | tee -a ".local/ci/doc_links.log"
    # Update status to 99
    tmp="$(mktemp)"
    awk 'BEGIN{OFS="\t"} $1=="doc_links"{$2=99} {print}' .local/ci/10_status.tsv > "$tmp" && mv "$tmp" .local/ci/10_status.tsv
  fi
fi

# (Restoration handled by trap)

# 4. Summary
echo "== Summary =="
echo "## Local Run Always Summary" > .local/ci/summary.md
echo "" >> .local/ci/summary.md
echo "| Step | Exit Code |" >> .local/ci/summary.md
echo "|---|---|" >> .local/ci/summary.md
if [ -f .local/ci/10_status.tsv ]; then
    cat .local/ci/10_status.tsv | while read -r name code; do
        echo "| $name | $code |" >> .local/ci/summary.md
        echo "Step: $name -> $code"
    done
fi

# 5. Final Aggregation
if [ -f .local/ci/10_status.tsv ]; then
    if awk '$2 != 0 {exit 1}' .local/ci/10_status.tsv; then
        echo "[PASS] All steps passed"
        exit 0
    else
        echo "[FAIL] Failures detected (check .local/ci/summary.md)"
        exit 1
    fi
else
    echo "[FAIL] No status file"
    exit 1
fi
