# S18-00 TASK — Deterministic Template Kit Bootstrap (v2)

## Safety Snapshot (recover-first; avoid unnecessary HALT)
- MIGRATED: S21-MIG-S18-0001 (see docs/ops/S21_TASK.md)
  - `cd "$(git rev-parse --show-toplevel)"`
- MIGRATED: S21-MIG-S18-0002 (see docs/ops/S21_TASK.md)
  - `git fetch -p origin`
- MIGRATED: S21-MIG-S18-0003 (see docs/ops/S21_TASK.md)
  - `git status -sb`
- MIGRATED: S21-MIG-S18-0004 (see docs/ops/S21_TASK.md)
  - MIGRATED: S21-MIG-S18-0005 (see docs/ops/S21_TASK.md)
    - `git push -u origin HEAD`
  - MIGRATED: S21-MIG-S18-0006 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S18-0007 (see docs/ops/S21_TASK.md)
  - MIGRATED: S21-MIG-S18-0008 (see docs/ops/S21_TASK.md)
    - `git diff --stat`
  - MIGRATED: S21-MIG-S18-0009 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S18-0010 (see docs/ops/S21_TASK.md)
      - `git add docs/ops docs/ops/meta 2>/dev/null || true`
    - then commit, OR stash, OR revert (choose one)
  - [x] re-check:
    - `git status -sb`
- [x] STOP ONLY if:
  - cannot reach a clean or explicitly-explained state (unknown contamination)

---

## 0) Branch (create or SKIP with reason)
- [x] `git switch main`
- [x] `git pull --ff-only`
- [x] create branch (if missing):
  - `git switch -c s18-00-kickoff-v1 2>/dev/null || echo "SKIP: branch already exists"`
- [x] `git status -sb`

---

## 1) Template Bootstrap (NO STOP on missing; missing is the deliverable)
### 1.1 Ensure meta directory
- [x] `test -d docs/ops/meta || mkdir -p docs/ops/meta`
- [x] `ls -la docs/ops | rg "meta" || true`

### 1.2 Check template existence (observation)
- [x] `test -f docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md || echo "MISSING: docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md"`
- [x] `test -f docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md || echo "MISSING: docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md"`

### 1.3 Create missing templates deterministically (NO overwrite)
- [x] run bootstrap writer (creates ONLY missing files; never overwrites existing)
  - `python - <<'PY'
from pathlib import Path

meta = Path("docs/ops/meta")
meta.mkdir(parents=True, exist_ok=True)

plan = meta / "DETERMINISTIC_PLAN_TEMPLATE.md"
task = meta / "DETERMINISTIC_TASK_TEMPLATE.md"

# Write PLAN template only if missing
if not plan.exists():
    plan.write_text("""# DETERMINISTIC_PLAN_TEMPLATE (v1)

## Goal
- {{GOAL_ONE_LINE}}

## Invariants (Must Hold)
- Planは分岐と停止条件（嘘をつかない）
- Canonicalは1回だけ固定（以降はObservations）
- skipは理由1行、errorはその場で停止
- 編集対象は実パス固定（探索→確定→記録）

## Inputs (SOT)
- {{SOT_PATHS}}

## Outputs (Deliverables)
- {{DELIVERABLES}}

## Gates
- make test PASS
- go run cmd/reviewpack/main.go submit --mode verify-only PASS

## Phase 0 — Scope Definition (STOP条件つき)
- if scope missing:
  - error: "scope missing; define explicitly before coding"

## Phase 1 — Define Deliverables
- Deliverable A: {{A}}
- Deliverable B: {{B}}

## Phase 2 — Implementation
- smallest safe steps + local gates

## Phase 3 — Final Gate & Canonical Pin (single)
- pin once: commit / bundle / sha256
- note: future verify-only outputs are Observations

## Phase 4 — PR Ritual
- Canonical block is written exactly once
""", encoding="utf-8")
    print("OK: wrote PLAN template")
else:
    print("SKIP: PLAN template exists (no overwrite)")

# Write TASK template only if missing
if not task.exists():
    task.write_text("""# DETERMINISTIC_TASK_TEMPLATE (v1)

## Safety Snapshot
- [x] cd repo root
- [x] git fetch -p origin
- [x] git status -sb (dirty/ahead -> resolve)

## Core Rules
- [x] Plan=分岐/停止条件
- [x] Task=順序固定チェックリスト
- [x] skip=理由1行 / error=その場で停止
""", encoding="utf-8")
    print("OK: wrote TASK template")
else:
    print("SKIP: TASK template exists (no overwrite)")
PY`
- [x] re-check presence (STOP only if still missing after creation attempt)
  - [x] `test -f docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md || echo "STOP: still missing PLAN template (write failure)"`
  - [x] `test -f docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md || echo "STOP: still missing TASK template (write failure)"`
- [x] list:
  - [x] `ls -la docs/ops/meta | rg "DETERMINISTIC_" || true`

STOP condition here:
- created-but-missing persists (write failure / permission / path)

---

## 2) Create S18 skeleton docs from templates (no overwrite)
- [x] set variables (path fixed):
  - `TPL_PLAN="docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md"`
  - `TPL_TASK="docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md"`
- [x] ensure templates exist (if not, STOP per Phase 1.3 rule)
  - `test -f "$TPL_PLAN" || echo "STOP: missing $TPL_PLAN"`
  - `test -f "$TPL_TASK" || echo "STOP: missing $TPL_TASK"`
- [x] create docs if missing:
  - [x] `test -f docs/ops/S18_PLAN.md    || cp "$TPL_PLAN" docs/ops/S18_PLAN.md`
  - [x] `test -f docs/ops/S18_TASK.md    || cp "$TPL_TASK" docs/ops/S18_TASK.md`
  - [x] `test -f docs/ops/S18-00_PLAN.md || cp "$TPL_PLAN" docs/ops/S18-00_PLAN.md`
  - [x] `test -f docs/ops/S18-00_TASK.md || cp "$TPL_TASK" docs/ops/S18-00_TASK.md`
- [x] verify existence:
  - [x] `ls -la docs/ops | rg "^.*S18" || true`

SKIP rule:
- if any target exists, do not overwrite; record 1-line SKIP in PR notes if needed

---

## 3) Scope Pin (edit contents now; prevent ex-post)
### 3.1 S18-00 scope statement (must match PLAN)
- [x] In `docs/ops/S18-00_PLAN.md`, set Goal (1 sentence):
  - `Deterministic ops templates (v1) を導入し、以後の全フェーズのPlan/Task生成を決定論に固定する。`
- [x] Ensure Deliverables list includes EXACT paths (6):
  - docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md
  - docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md
  - docs/ops/S18_PLAN.md
  - docs/ops/S18_TASK.md
  - docs/ops/S18-00_PLAN.md
  - docs/ops/S18-00_TASK.md

### 3.2 S18 epic minimal header (future phases blocked until defined)
- [x] In `docs/ops/S18_PLAN.md`, write minimal:
  - `S18-00: Template kit bootstrap (this PR)`
  - `S18-01+: TBD (must be defined in ops docs before starting)`

STOP rule:
- If scope text diverges from this TASK, fix the docs now (no ambiguity)

---

## 4) Local Gates (quality gate; stop if fails)
- [x] `make test`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [x] if fail:
  - [x] capture failing output (log path or pasted snippet)
  - [x] fix
  - [x] re-run gates

---

## 5) Canonical Pin (single for this PR)
- [x] Decide Canonical = THIS PR's result only (Observations are not Canonical)
- [x] Record:
  - [x] Commit SHA (after commit)
  - [x] Review Bundle filename
  - [x] SHA256

---

## 6) Commit (docs-only)
- [x] stage:
  - `git add docs/ops/meta docs/ops/S18*`
- [x] confirm:
  - `git diff --cached --stat`
- [x] commit:
  - `git commit -m "chore(ops): bootstrap deterministic templates v1 + kickoff S18-00"`
- [x] status:
  - `git status -sb`

---

## 7) Push / PR
- [x] push:
  - `git push -u origin HEAD`
- [x] PR:
  - `gh pr create --fill`
- [x] PR body includes Canonical block EXACTLY once:
  - Commit: `________`
  - Review Bundle: `review_bundle_YYYYMMDD_HHMMSS.tar.gz`
  - SHA256: `________`
  - Note: Future verify-only outputs are Observations (no Canonical update)
