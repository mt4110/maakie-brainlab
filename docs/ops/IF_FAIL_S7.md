# IF_FAIL_S7: CI & Verification Failure Playbook

This document outlines how to diagnose and resolve failures in the S7 Continuous Integration pipeline.

## IF-01: Download Fail
**Symptom**: `ops/ci/verify_pack_ci.sh` fails at the download stage.
**Log**: `verify_download.log` (or console output).
**Checks**:
1.  Is `EVIDENCE_PACK_URL` set correctly?
2.  Is the URL accessible from the CI runner (network policies)?
3.  Does the file exist at the source?

## IF-02: SHA Mismatch
**Symptom**: Download succeeded, but SHA256 verification failed.
**Log**: `verify_sha256.log`
**Checks**:
1.  **Corruption**: Download the file locally and check `shasum -a 256`.
2.  **Wrong Hash**: Is `EVIDENCE_PACK_SHA256` matching the artifact?
3.  **Attack**: If corruption is ruled out, the artifact might be compromised. **STOP and escalate.**

## IF-03: Kind Missing
**Symptom**: `verify_pack.sh` reports `[FAIL] Unknown pack format`.
**Log**: `verify_dispatch.log` or console.
**Checks**:
1.  Inspect the tarball content: `tar -tf <pack>`.
2.  Look for `evidence_pack_v1` (root) or `review_pack_v1` (nested).
3.  **Action**: If missing, the pack generation (S5) is broken. Fix `ops/s5_pack.sh` or `cmd/reviewpack`.

## IF-04: Dispatcher Fail
**Symptom**: `ops/verify_pack.sh` fails to route to the correct verifier.
**Log**: `verify_dispatch.log`.
**Checks**:
1.  Check `Detecting...` output in logs.
2.  If it detects wrong kind, check for ambiguous files (e.g., both markers present).

## IF-05: Inner Verify Fail
**Symptom**: The artifact is valid, but internal verification (`make verify-pack` or `VERIFY*.sh`) fails.
**Log**: `verify_pack.log`.
**Checks**:
1.  **Checksum Mismatch**: File corruption or tampering inside the pack.
2.  **Signature Fail**: GPG signature invalid. Check `S6_VERIFY_KEY` matches the signing key.
3.  **Content Fail**: `latest.jsonl` missing or invalid.

## IF-07: Strict Mode Failure (Exit 5)
**Symptom**: `submit --mode strict` or `make s5` fails with `exit status 5`.
**Log**: `31_make_run_eval.log` (internal to pack or in artifacts).
**Checks**:
1.  **LLM Server**: Is the local LLM server running? (`make server-status`)
2.  **Verify-Only Leak**: If this happens in GitHub-hosted CI, it's a critical bug. CI should NEVER run strict mode. Check `GATE1_VERIFY_ONLY` env var.
3.  **Evidence**: Check `eval/results/latest.jsonl` permissions and content.

## IF-06: Upload Fail
**Symptom**: CI finishes but artifacts are not in the storage/output location.
**Log**: GitHub Actions "Upload Artifact" step logs.
**Checks**:
1.  Did the job cancel early? ensure `if: always()` is used for upload steps.
2.  Is the `out/` directory empty?
3.  Check retention policy settings.
