# INJECTION_SIM_SUITE_v1 — Attack Case Catalog (Light)
Last Updated: 2026-02-24

## Purpose
A minimal, CPU-light catalog of “how attackers try to steer or corrupt the system”.
This is a **documentation-driven suite**:
- It must stay small (5–10 cases)
- Each case states the *expected behavior* (OK/ERROR/SKIP)
- Fixtures are optional; if referenced, they must be **relative paths**

## Case Format (v1)
- id: SIM-XXX
- category: traversal | injection | nondeterminism | archive | supply_chain | ops_hygiene
- target_surface: IL | docs | pack | scripts | CI | operator
- vector: short description
- expected: OK | ERROR | SKIP
- fixture_path: (optional) relative path
- notes: short

---

### SIM-001
- category: injection
- target_surface: IL
- vector: untrusted text attempts to become control instructions (prompt/trace hijack)
- expected: ERROR
- fixture: (optional) docs/il/examples/bad_forbidden_timestamp__trace_injection.json
- notes: should be detected as forbidden/injection channel, never executed as control

### SIM-002
- category: traversal
- target_surface: IL
- vector: path includes `../` or absolute path, attempting to escape sandbox
- expected: ERROR
- fixture: (optional) (none)
- notes: validator/executor must reject or sanitize; log must be explicit

### SIM-003
- category: nondeterminism
- target_surface: pack
- vector: timestamp/locale/env contamination changes hash with same semantics
- expected: ERROR
- fixture: (optional) (none)
- notes: canonicalization should eliminate drift or flag forbidden fields

### SIM-004
- category: archive
- target_surface: pack
- vector: tar metadata drift (uid/gid, order, pax headers) to bypass equality checks
- expected: ERROR
- fixture: (optional) (none)
- notes: pack rules must neutralize unstable metadata

### SIM-005
- category: supply_chain
- target_surface: scripts
- vector: dependency/toolchain behavior changes unexpectedly (version drift)
- expected: SKIP
- fixture: (optional) (none)
- notes: v1 only documents detection strategy; stronger controls are future work

### SIM-006
- category: ops_hygiene
- target_surface: operator
- vector: untracked helper scripts accidentally included in PR/evidence
- expected: ERROR
- fixture: (optional) (none)
- notes: quarantine untracked into .local/tmp; logs must show action

### SIM-007
- category: injection
- target_surface: docs
- vector: malicious doc content tries to influence review tools (marker injection, hidden directives)
- expected: ERROR
- fixture: (optional) (none)
- notes: tools must treat docs as data; no execution path

### SIM-008
- category: traversal
- target_surface: scripts
- vector: user-provided input used in shell command without quoting/sanitization
- expected: ERROR
- fixture: (optional) (none)
- notes: enforce safe quoting, avoid eval, avoid glob
