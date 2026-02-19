# S21-06_PLAN (v1)

## Goal

- S21-06: IL scripts hardening (Copilot A→B 回収) - exit/SystemExit禁止, 止まらない, 監査ログ真実

## Invariants (Must Hold)

- Planは分岐と停止条件（嘘をつかない）
- Canonicalは1回だけ固定（以降はObservations）
- skipは理由1行、errorはその場で停止
- 編集対象は実パス固定（探索→確定→記録）
- **exit/SystemExit禁止**
- **ログは必ず OK:/ERROR:/SKIP: で始まる**
- **レポートファイルは必ず生成される**

## Inputs (SOT)

- docs/ops/S21-05_PLAN.md (Predecessor)
- scripts/il_guard.py
- scripts/il_exec.py
- scripts/il_check.py
- tests/fixtures/il/good/minimal.json

## Outputs (Deliverables)

- scripts/{il_guard,il_exec,il_check}.py (Hardened)
- tests/fixtures/il/good/minimal.json (Timestamp removed)

## Gates

- make test PASS
- go run cmd/reviewpack/main.go submit --mode verify-only PASS
- scripts/il_check.py (Internal verification) PASS

## Phase 0 — Scope Definition (STOP条件つき)

- IF not in git repo: print ERROR and STOP
- IF S21-05(PR72) not merged: print SKIP (S21-06は追いPRなので) and continue

## Phase 1 — Define Deliverables

- Deliverable A: A1 (fixture cleanup), A2 (guard/canonical hardening), A3 (no SystemExit), A4 (no shell=True)
- Deliverable B: B1 (always report), B2 (log prefixes), B3 (exec status aggregation), B4 (check hardening)

## Phase 2 — Implementation (Pseudo-code)

### A1: Fixture Cleanup

- Remove timestamp from `tests/fixtures/il/good/minimal.json`
- IF diff not as expected: print ERROR and STOP

### A2/A3/A4 + B: Hardening

- **il_guard:**
  - validation: use `ILValidator`, record strict errors (E_FORBIDDEN)
  - canonical: `ILCanonicalizer.canonicalize` on sanitized input (forbidden removed)
  - dump: `allow_nan=False`
  - robustness: try/except -> always write `il.guard.json` (fallback to "."), no SystemExit

- **il_exec:**
  - pre-check: if `guard.can_execute` false -> SKIP, write `il.exec.json`
  - loop: log `OK:`/`ERROR:`/`SKIP:`
  - status: aggregate (ERROR > OK > SKIP)
  - robustness: always write `il.exec.json`

- **il_check:**
  - subprocess: `shell=False`, argv list
  - control: ignore return code, read generated reports
  - robustness: try/except -> print ERROR, keep going

## Phase 3 — Final Gate & Canonical Pin (single)

- pin once: commit / bundle / sha256

## Phase 4 — PR Ritual

- Canonical block is written exactly once
