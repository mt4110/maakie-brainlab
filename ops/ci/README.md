# ops/ci

This directory contains scripts and configuration for the S7 Continuous Integration pipeline.

## Scripts
-   `verify_pack_ci.sh`: Main entry point for CI pack verification (Planned S7-C04).

## Usage
These scripts are designed to be run by GitHub Actions (`.github/workflows/verify_pack.yml`) but can be tested locally if environment variables (`EVIDENCE_PACK_URL`, etc.) are set.
