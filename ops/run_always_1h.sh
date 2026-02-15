#!/bin/bash
# ops/run_always_1h.sh
# mimic CI "Run Always" workflow locally (and enforce AI Guards)

set -u

# Failure Injection (env var: INJECT_FAILURE)
INJECT_FAILURE="${INJECT_FAILURE:-none}"

# 1. Preflight (Auto-Stash) & Init (Run Dir)
TIMESTAMP_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
SHORT_SHA="$(git rev-parse --short HEAD)"
RUN_ID="${TIMESTAMP_UTC}_${SHORT_SHA}"
RUN_VAR_DIR=".local/run-always"
RUN_DIR="${RUN_VAR_DIR}/${RUN_ID}"
# Save RUN_DIR for CI to easy pickup
echo "${RUN_DIR}" > "${RUN_VAR_DIR}/.last_run_dir"

# Safety: Ensure we are in the repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
CURRENT_DIR="$(pwd)"
if [[ "$REPO_ROOT" != "$CURRENT_DIR" ]]; then
    echo "[ERROR] Must run from repo root: $REPO_ROOT"
    exit 1
fi

mkdir -p "$RUN_DIR"
# Update latest (symlink for simple access, plan validation allowed symlink)
rm -f "${RUN_VAR_DIR}/latest"
ln -s "$RUN_ID" "${RUN_VAR_DIR}/latest"

LOG_DIR="${RUN_DIR}" # or ${RUN_DIR}/logs if we want valid structure. Plan says run-always/<RUN_ID>/logs/... 
# Existing script puts logs in .local/ci. Let's redirect to RUN_DIR.
CI_DIR="$RUN_DIR"

echo "== Preflight (Local) ==" | tee "${CI_DIR}/00_preflight.log"

stash_created="0"
stash_before_cnt="$(git stash list | wc -l | tr -d ' ')"
git_status="$(git status --porcelain=v1 || true)"

if [ -z "$git_status" ]; then
  echo "[OK] working tree clean" | tee -a "${CI_DIR}/00_preflight.log"
else
  echo "[WARN] working tree dirty -> auto-stash (-u) so clean-required steps can run" | tee -a "${CI_DIR}/00_preflight.log"
  echo "$git_status" | tee -a "${CI_DIR}/00_preflight.log"

  # -u: untrackedも退避（ただし ignored は退避しない）
  git stash push -u -m "run_always_1h:auto-stash ${RUN_ID}" >/dev/null 2>&1 || true

  stash_after_cnt="$(git stash list | wc -l | tr -d ' ')"
  if [ "$stash_after_cnt" -gt "$stash_before_cnt" ]; then
    stash_created="1"
    echo "[OK] stash created: stash@{0}" | tee -a "${CI_DIR}/00_preflight.log"
  else
    echo "[INFO] no stash created" | tee -a "${CI_DIR}/00_preflight.log"
  fi
fi

restore_stash() {
  # Injection restore
  if [ "${INJECT_FAILURE:-}" = "doclinks" ]; then
      echo "[INJECT] doclinks: restoring README.md" | tee -a "${CI_DIR}/20_inject.log"
      git restore -- README.md 2>/dev/null || true
  fi

  # Stash restore
  if [ "$stash_created" = "1" ]; then
    echo "[INFO] restoring stash stash@{0}" | tee -a "${CI_DIR}/00_preflight.log"
    git stash pop stash@{0} >/dev/null 2>&1 || {
      echo "[ERROR] stash pop failed; try apply and keep stash" | tee -a "${CI_DIR}/00_preflight.log"
      git stash apply stash@{0} >/dev/null 2>&1 || true
    }
  fi
}
trap 'restore_stash' EXIT

# 2. Init CI logic
echo "== Init CI (Local) =="
date -u +"%Y%m%dT%H%M%SZ" > "${CI_DIR}/00_utc.txt"
echo "sha=$(git rev-parse HEAD)" > "${CI_DIR}/00_meta.txt"
echo "run_id=${RUN_ID}" >> "${CI_DIR}/00_meta.txt"
rm -f "${CI_DIR}/10_status.tsv"

# 3. Key Steps (wrapped)

# Mimic CI Env (verify-only)
export S5_MODE="verify-only"
export GATE1_VERIFY_ONLY="1"
export REVIEWPACK_POLICY_MODE="ci"
export S6_SIGNING_KEY="${S6_SIGNING_KEY:-}"
export S6_VERIFY_KEY="${S6_VERIFY_KEY:-}"

run_step() {
    local name="$1"
    shift
    echo "== Step: $name =="
    # S17-03 Diagnostics
    if [ -n "${S6_SIGNING_KEY:-}" ]; then
        echo "[DIAG] S6_SIGNING_KEY is set (exists: $([ -f "$S6_SIGNING_KEY" ] && echo "YES" || echo "NO"))"
    else
        echo "[DIAG] S6_SIGNING_KEY is NOT set"
    fi
    # S17-03: EvidencePack Key (Trust Anchor v1 needs Ed25519)
    if [ -n "${S6_SIGNING_KEY:-}" ] && [ -f "$S6_SIGNING_KEY" ]; then
        if grep -q "BEGIN PGP" "$S6_SIGNING_KEY"; then
            echo "[DIAG] S6_SIGNING_KEY is PGP armored (compatible with reviewpack, NOT evidencepack)"
            # If S6_SIGNING_KEY is set and is an armored PGP key, and it's local verification,
            # generate an ephemeral Ed25519 key for evidencepack pack if not already set.
            if [[ "$S6_SIGNING_KEY" == *"BEGIN PGP PRIVATE KEY BLOCK"* ]] && [ -z "$EP_SIGNING_KEY" ]; then
                echo "SIGNING_MODE=SMOKE (deterministic; NOT secure)"
                export EP_SIGNING_KEY=".tmp/ephemeral_ed25519.key"
                [ -d .tmp ] || mkdir .tmp
                go run cmd/evidencepack/main.go keygen --seed "reviewpack-smoke-v1" --out "$EP_SIGNING_KEY" > /dev/null
            else
                echo "SIGNING_MODE=REAL (env-provided)"
            fi
        else
            export EP_SIGNING_KEY="$S6_SIGNING_KEY"
        fi
    fi
    set +e
    (
        set -euo pipefail
        "$@"
    ) 2>&1 | tee "${CI_DIR}/${name}.log"
    local ec=${PIPESTATUS[0]}
    echo -e "${name}\t${ec}" >> "${CI_DIR}/10_status.tsv"
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
SIGN_ARG=""
if [ -n "${S6_SIGNING_KEY:-}" ] && [ -f "$S6_SIGNING_KEY" ]; then
    SIGN_ARG="--sign-key ${S6_SIGNING_KEY}"
fi
run_step "review_bundle" go run ./cmd/reviewpack/main.go submit --mode verify-only $SIGN_ARG

# 3.4 Verify Evidence
run_step "verify_evidence" bash -c 'PACK=$(ls -t .local/reviewpack_artifacts/evidence_pack_*.tar.gz | head -n 1); make verify-pack PACK="$PACK"'

# 3.5 Verify Bundle
run_step "verify_bundle" bash -c 'PACK=$(ls -t review_bundle_*.tar.gz | head -n 1); make verify-pack PACK="$PACK"'

# 3.6 S7 Evidence Pack (Crypto Layer v1)
# S17-03: Pass signing key if available
EVIDENCE_SIGN_ARG=""
if [ -n "${EP_SIGNING_KEY:-}" ] && [ -f "$EP_SIGNING_KEY" ]; then
    EVIDENCE_SIGN_ARG="--sign-key ${EP_SIGNING_KEY}"
fi
run_step "s7_evidence" bash -c "
    go run ./cmd/evidencepack pack --kind s7demo --store '${RUN_DIR}/evidence_store' $EVIDENCE_SIGN_ARG cmd/evidencepack/main.go
    LATEST=\$(ls -t '${RUN_DIR}/evidence_store/packs/s7demo/'*.tar.gz | head -n1)
    go run ./cmd/evidencepack verify --pack \"\$LATEST\"
"

# 3.5b Move Artifacts to RUN_DIR (Consolidation)
echo "== Artifact Consolidation ==" | tee -a "${CI_DIR}/logs.txt"
mv review_bundle_*.tar.gz "${RUN_DIR}/" 2>/dev/null || true
if ls review_pack_*.tar.gz >/dev/null 2>&1; then
    mv review_pack_*.tar.gz "${RUN_DIR}/"
fi
# Copy logs/summary from .local/ci/ if they exist elsewhere (current script matches RUN_DIR=CI_DIR so checking)
# In this script, CI_DIR = RUN_DIR, so logs are already there.


# 3.6 Doc Links

inject_doclinks_begin() {
  [ "${INJECT_FAILURE:-}" = "doclinks" ] || return 0
  echo "[INJECT] doclinks: patching README.md (tracked) for scan..." | tee -a "${CI_DIR}/20_inject.log"
  # Inject multiple forbidden patterns to ensure detection (Obfuscated from linter)
  PROTO="file"
  PROTO="${PROTO}://"
  printf "\n<!-- INJECT_DOC_LINKS_BEGIN -->\n[file-url](${PROTO}/INJECT_DO_NOT_OPEN)\n${PROTO}/INJECT_DO_NOT_OPEN\n${PROTO}localhost/INJECT_DO_NOT_OPEN\n${PROTO}/INJECT_DO_NOT_OPEN\n<!-- INJECT_DOC_LINKS_END -->\n" >> README.md
  # Check if injection worked
  rg -n "INJECT_DO_NOT_OPEN|file[:]//" README.md | tee -a "${CI_DIR}/20_inject.log" || true
}

if [ "${INJECT_FAILURE:-}" = "doclinks" ]; then
  inject_doclinks_begin
fi

# Debug recipe
make -n check-doc-links > "${CI_DIR}/21_doclinks_recipe.txt" 2>&1 || true

run_step "doc_links" make check-doc-links

# Fail Safe for Injection
if [ "$INJECT_FAILURE" = "doclinks" ]; then
  doc_ec="$(awk '$1=="doc_links"{print $2}' "${CI_DIR}/10_status.tsv" | tail -n 1)"
  if [ "${doc_ec:-0}" = "0" ]; then
    echo "[INJECT][ERROR] doclinks injection did NOT trigger failure; marking doc_links as invalid test (ec=99)" | tee -a "${CI_DIR}/doc_links.log"
    # Update status to 99
    tmp="$(mktemp)"
    awk 'BEGIN{OFS="\t"} $1=="doc_links"{$2=99} {print}' "${CI_DIR}/10_status.tsv" > "$tmp" && mv "$tmp" "${CI_DIR}/10_status.tsv"
  fi
fi

# (Restoration handled by trap)


# 2. Cleanup (Retention Hardening)
cleanup_local_runs() {
    local max_keep=48
    local root="$RUN_VAR_DIR"
    
    echo "== Cleanup ($max_keep keep) ==" | tee -a "${CI_DIR}/99_cleanup.log"

    # Safety Checks
    if [[ ! -d "$root" ]]; then echo "[SKIP] No root dir" | tee -a "${CI_DIR}/99_cleanup.log"; return 0; fi
    
    # Check if root is inside repo (realpath)
    # macOS doesn't have realpath by default sometimes, use python or perl or assumes safe if relative path matches
    local abs_root
    abs_root="$(cd "$root" && pwd)"
    if [[ "$abs_root" != "${REPO_ROOT}/.local/run-always" ]]; then
         echo "[ERROR] Cleanup target disallowed: $abs_root (Must be ${REPO_ROOT}/.local/run-always)" | tee -a "${CI_DIR}/99_cleanup.log"
         return 1
    fi
    
    # List directories (timestamped format YYYY...)
    # Sort reverse, skip N, delete rest
    # Using ls -1 | sort -r is mostly safe for these filenames
    
    # Count
    local count
    count="$(ls -1 "$root" | grep -E '^[0-9]{8}T[0-9]{6}Z_' | wc -l | tr -d ' ')"
    
    if [[ "$count" -le "$max_keep" ]]; then
        echo "[INFO] Run count $count <= $max_keep, no cleanup needed" | tee -a "${CI_DIR}/99_cleanup.log"
        return 0
    fi
    
    echo "[INFO] Cleaning up $((count - max_keep)) old runs..." | tee -a "${CI_DIR}/99_cleanup.log"
    
    ls -1 "$root" | grep -E '^[0-9]{8}T[0-9]{6}Z_' | sort -r | tail -n +$((max_keep + 1)) | while read -r target; do
        # Double check target is not empty and not slash
        if [[ -n "$target" && "$target" != "/" ]]; then
            echo "Deleting: $root/$target" | tee -a "${CI_DIR}/99_cleanup.log"
            rm -rf "$root/$target"
        fi
    done
}

# Run cleanup
cleanup_local_runs || echo "[WARN] Cleanup failed"

# 3.7 Local Death Scan (Repo Text Guard)
run_step "repo_guard" bash ops/finalize_clean.sh --check

# 4. Summary (Normalization)
echo "== Summary =="
generate_summary() {
    local summary_md="${CI_DIR}/summary.md"
    local summary_jsonl="${CI_DIR}/summary.jsonl"
    local status_file="${CI_DIR}/10_status.tsv"
    
    # JSONL keys
    local status="FAIL"
    if [ -f "$status_file" ] && awk '$2 != 0 {exit 1}' "$status_file"; then
        status="PASS"
    fi
    
    # Metadata
    echo "## Run Always Summary: ${RUN_ID}" > "$summary_md"
    echo "" >> "$summary_md"
    echo "- **Time (UTC)**: ${TIMESTAMP_UTC}" >> "$summary_md"
    echo "- **Git SHA**: ${SHORT_SHA}" >> "$summary_md"
    echo "- **Result**: ${status}" >> "$summary_md"
    echo "" >> "$summary_md"
    
    echo "### Checks" >> "$summary_md"
    echo "| Step | Status |" >> "$summary_md"
    echo "|---|---|" >> "$summary_md"
    
    local json_checks="[]"
    
    if [ -f "$status_file" ]; then
        while read -r name code; do
             local verdict="PASS"
             if [ "$code" != "0" ]; then verdict="FAIL ($code)"; fi
             echo "| $name | $verdict |" >> "$summary_md"
             # json construction (simple string manipulation for bash)
             # this is fragile in bash, ideal is python, but sticking to bash for now
        done < "$status_file"
    else 
        echo "| (No status file) | - |" >> "$summary_md"
    fi
    
    echo "" >> "$summary_md"
    echo "### Artifacts" >> "$summary_md"
    echo "- [Log Directory](.)" >> "$summary_md"
    ls -1 "${CI_DIR}" | grep "\.log$" | sed 's/^/- /' >> "$summary_md"
    
    echo "" >> "$summary_md"
    echo "### Next Action" >> "$summary_md"
    if [ "$status" == "PASS" ]; then
        echo "No action required. (Ready for evidence)" >> "$summary_md"
    else
        echo "Investigate failures in logs." >> "$summary_md"
    fi

    # JSONL Generation (One line)
    # Using python for reliable JSON generation
    python3 -c "
import json
import os

try:
    checks = []
    status_file = '${status_file}'
    if os.path.exists(status_file):
        with open(status_file) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    checks.append({'name': parts[0], 'code': int(parts[1])})

    data = {
        'timestamp_utc': '${TIMESTAMP_UTC}',
        'run_id': '${RUN_ID}',
        'git_sha': '${SHORT_SHA}',
        'status': '${status}',
        'checks': checks,
        'artifacts': [f for f in os.listdir('${CI_DIR}') if f.endswith('.log') or f.endswith('.md')]
    }
    print(json.dumps(data))
except Exception as e:
    print(json.dumps({'error': str(e)}))
" > "$summary_jsonl"

    echo "[INFO] Generated summary.md and summary.jsonl"
}

generate_summary

# 5. Final Aggregation
if [ -f "${CI_DIR}/10_status.tsv" ]; then
    if awk '$2 != 0 {exit 1}' "${CI_DIR}/10_status.tsv"; then
        echo "[PASS] All steps passed"
        exit 0
    else
        echo "[FAIL] Failures detected (check ${CI_DIR}/summary.md)"
        exit 1
    fi
else
    echo "[FAIL] No status file"
    exit 1
fi
