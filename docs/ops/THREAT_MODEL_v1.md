# THREAT_MODEL_v1 — Public Durability Outer Wall
Last Updated: 2026-02-24

## Scope
This document models threats against:
- Deterministic evidence workflows (review bundles, audit artifacts)
- IL (Intermediate Language) inputs/outputs and validation/execution surfaces
- Local/CI automation (scripts, runners, packaging)
- Public contributions (PRs, forks, external inputs)

Non-goals (v1):
- Full formal verification
- Full supply-chain attestation beyond current contracts

## Assets to Protect
- **Evidence integrity**: artifacts must be reproducible and tamper-evident
- **Determinism**: outputs must not drift due to timestamps, locale, env leakage
- **Operator safety**: no workflows that crash parent terminals or freeze tooling
- **Review trust**: logs must reflect truth (OK/ERROR/SKIP), not “silent pass”

## Attacker Model
- External contributor submitting malicious inputs via PR
- Local adversary (malware) modifying files in working tree
- Accidental operator error (untracked files, wrong branch, wrong milestone)
- Dependency or toolchain compromise (less likely, high impact)

## Trust Boundaries
- Repo content (tracked) vs working tree (untracked)
- Local runs vs CI runs
- Artifacts intended for audit vs temporary scratch

## Primary Attack Surfaces & Threats

### 1) Path Traversal / Unsafe File Access
**Vector**: crafted paths in IL or configs (e.g., `../`, absolute paths).  
**Impact**: reading/writing outside intended dirs; exfiltration; corruption.  
**Mitigations**:
- Canonicalize and validate paths at boundaries
- Enforce relative paths in docs/specs
- Quarantine untracked files to prevent accidental inclusion
**Detection artifacts**:
- Logs: `ERROR: path_traversal_detected ...`
- Static checks: docs/spec rules; IL validator rules

### 2) Prompt / Trace Injection (Instruction Hijacking)
**Vector**: text fields containing “do X” directives, hidden markers, or tool triggers.  
**Impact**: runtime behavior change, policy bypass, data leakage.  
**Mitigations**:
- Strict schema + canonicalization
- Forbidden field enforcement (timestamp/trace/instruction channels)
- Treat untrusted text as data; never as control
**Detection artifacts**:
- IL eval cases & injection sim suite
- Logs with explicit `ERROR: injection_detected ...`

### 3) Timestamp Contamination / Non-Determinism
**Vector**: inserting timestamps, locale/timezone leaks, unstable ordering.  
**Impact**: evidence drift; reproducibility break.  
**Mitigations**:
- Deterministic timestamps / forbidden timestamp fields
- Stable ordering & canonical formats
**Detection artifacts**:
- Canonicalize tests, pack diff checks, IL examples

### 4) Archive / Tar Canonicalization Bypass
**Vector**: PAX headers, uid/gid drift, filename ordering manipulation.  
**Impact**: hash changes without semantic changes; audit confusion.  
**Mitigations**:
- Canonical tar creation rules
- Strip unstable metadata
**Detection artifacts**:
- Bundle verification logs; pack diff tools; audit contracts

### 5) Supply Chain (Dependencies / Tools)
**Vector**: compromised dependency or runner environment.  
**Impact**: silent injection into build/test outputs.  
**Mitigations**:
- Pinning where feasible; minimal tool surface
- Evidence logs that record tool versions / environment summary (non-sensitive)
**Detection artifacts**:
- CI logs; audit chain artifacts; reproducibility checks

## Expected Failure Modes (How We Want It To Break)
- Prefer **loud, logged failure** over silent pass:
  - `ERROR: ...` should appear in logs
  - The workflow should remain stopless (no terminal crash)
- When something cannot be validated safely:
  - `SKIP: ...` with a single-line reason

## Residual Risks (Known Limits)
- v1 does not guarantee automatic CI failure for every ERROR log (policy: stopless)
- Some advanced supply-chain attacks require stronger attestation layers (future phases)
