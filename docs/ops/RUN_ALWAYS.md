# Run Always 1h (Scheduled Validation)

This document describes the **Run Always 1h** automated workflow,
designed to provide a continuous baseline for the project's health.

## 1. Overview

- **Frequency**: Every 4 hours (`0 */4 * * *`)
- **Workflow**: `.github/workflows/run_always_1h.yml` (Scheduled)
  - *Note*: `.github/workflows/verify_pack.yml` is for verification/pack only (PR/Push).
- **Script (Local)**: `ops/run_always_1h.sh`
- **Purpose**: Detect flakey tests, environment drift, and establish a reliable dataset for future analysis (S6).

## 2. Output & Retention

### 2.1 GitHub Actions (Remote)

- **Artifacts**: `run-always-<RUN_NUMBER>-<SHA>`
- **Retention**: **5 days**
- **Contents**:
  - `.local/ci/` (Logs, Summary)
  - `ci_out/`
  - `review_bundle_*.tar.gz`

### 2.2 Local Execution (On your machine)

- **Root Directory**: `.local/run-always/`
- **Structure**:

    ```text
    .local/run-always/
    ├── <TIMESTAMP_UTC>_<SHORT_SHA>/  (Run ID)
    │   ├── 00_meta.txt
    │   ├── review_bundle_*.tar.gz  (Consolidated artifact)
    │   ├── summary.md
    │   ├── summary.jsonl
    │   └── ...
    └── latest -> <TIMESTAMP_UTC>_<SHORT_SHA>
    ```

- **Retention Policy**: **Keep Last 48 Runs**
  - The `ops/run_always_1h.sh` script automatically deletes runs older than the newest 48.
  - Cleanup is strictly limited to `.local/run-always/` for safety.

## 3. How to Read the Summary

A normalized `summary.md` is generated for every run.

### Format

1. **Header**: Run ID (Timestamp + SHA)
2. **Environment**: Time (UTC), Git SHA, Status (PASS/FAIL)
3. **Checks**: Table of key steps and their exit codes.
4. **Artifacts**: List of generated logs and files.
5. **Next Action**: "No action required" or "Investigate failures".

### Artifacts to Check on Failure

- `summary.md`: High-level overview.
- `verify_pack.log`: Full output of the verification process.
- `gate1.log`: Unit tests and primary checks.
- `doc_links.log`: Documentation link check failures.

## 4. Failure Recovery (1-Scroll)

If the scheduled run fails:

1. **Check `summary.md`** in the artifact to identify the failing step.
2. **Reproduce Locally**:

    ```bash
    # Run the exact same script
    bash ops/run_always_1h.sh
    
    # Check the local summary
    cat .local/run-always/latest/summary.md
    ```

3. **Fix & Verify**:
    - Fix the issue.
    - Run the script again.
4. **Manual Trigger (Optional)**:
    - Go to GitHub Actions -> "Verify Pack" -> "Run workflow".

## 5. Normalized Data (S6 Ready)

- `summary.jsonl`: Machine-readable JSON line containing strict types and paths.
- Used for aggregating long-term stability metrics.
