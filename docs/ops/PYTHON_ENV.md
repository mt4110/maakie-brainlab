# Python Environment Canonicalization (S20-08)

## Overview
This repository enforces a **single canonical Python environment** to eliminate drift between local development and CI/CD.

- **Interpreter**: `.venv/bin/python` (Always)
- **Dependency Manager**: `uv` (via `uv.lock`)
- **Bootstrap**: `make bootstrap` (Installs `uv` if needed, then syncs)

## Quick Start

### 1. Bootstrap
To set up or refresh your environment (safe to run repeatedly):
```bash
make bootstrap
```
*Note: This command will install `uv` (via `pip install uv`) if not present, and then run `uv sync`.*

### 2. Run Tests
```bash
make test
```
*Note: This ensures tests run inside `.venv/bin/python`.*

### 3. Check Environment Status
If you suspect environment issues, run the guardrail script:
```bash
make py-env-report
```
Expected output:
- `is_venv`: `True` (or consistent with `.venv` path)
- `sys.executable`: `.../.venv/bin/python`

## Rules & Prohibitions

### ❌ DO NOT
- **Do NOT run `pip install -r requirements.txt`**. usage of `requirements.txt` is deprecated and removed.
- **Do NOT use `pip --user`** to install dependencies for this repo. It causes confusion with system packages.
- **Do NOT use system python** for repository tasks (except initial `make bootstrap`).

### ✅ DO
- **DO use `make bootstrap`** as the single source of truth for setup.
- **DO use `.venv/bin/python`** or `make` targets for execution.
- **DO commit `uv.lock`** when dependencies change.

## Troubleshooting
If `.venv` is broken or behavior is inconsistent:
1.  Verify you are in the repo root.
2.  Run `rm -rf .venv`
3.  Run `make test` to verify basic correctness.
4.  Run `make py-env-report` to verify.
