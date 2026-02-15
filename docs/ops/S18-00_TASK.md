# S18-00 TASK — Deterministic Template Kit Bootstrap (v2)

## Safety Snapshot (recover-first; avoid unnecessary HALT)
- [ ] cd repo root:
  - `cd "$(git rev-parse --show-toplevel)"`
- [ ] fetch:
  - `git fetch -p origin`
- [ ] observe status:
  - `git status -sb`
- [ ] if ahead:
  - [ ] either push:
    - `git push -u origin HEAD`
  - [ ] OR record reason (1 line) and proceed (no silent continue)
- [ ] if dirty:
  - [ ] inspect:
    - `git diff --stat`
  - [ ] resolve to clean (docs-only is preferred):
    - stage docs if appropriate:
      - `git add docs/ops docs/ops/meta 2>/dev/null || true`
    - then commit, OR stash, OR revert (choose one)
  - [ ] re-check:
    - `git status -sb`
- [ ] STOP ONLY if:
  - cannot reach a clean or explicitly-explained state (unknown contamination)

---

## 0) Branch (create or SKIP with reason)
- [ ] `git switch main`
- [ ] `git pull --ff-only`
- [ ] create branch (if missing):
  - `git switch -c s18-00-kickoff-v1 2>/dev/null || echo "SKIP: branch already exists"`
- [ ] `git status -sb`

---

## 1) Template Bootstrap (NO STOP on missing; missing is the deliverable)
### 1.1 Ensure meta directory
- [ ] `test -d docs/ops/meta || mkdir -p docs/ops/meta`
- [ ] `ls -la docs/ops | rg "meta" || true`

### 1.2 Check template existence (observation)
- [ ] `test -f docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md || echo "MISSING: docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md"`
- [ ] `test -f docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md || echo "MISSING: docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md"`

### 1.3 Create missing templates deterministically (NO overwrite)
- [ ] run bootstrap writer (creates ONLY missing files; never overwrites existing)
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
- [ ] cd repo root
- [ ] git fetch -p origin
- [ ] git status -sb (dirty/ahead -> resolve)

## Core Rules
- [ ] Plan=分岐/停止条件
- [ ] Task=順序固定チェックリスト
- [ ] skip=理由1行 / error=その場で停止
""", encoding="utf-8")
    print("OK: wrote TASK template")
else:
    print("SKIP: TASK template exists (no overwrite)")
PY`
- [ ] re-check presence (STOP only if still missing after creation attempt)
  - [ ] `test -f docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md || echo "STOP: still missing PLAN template (write failure)"`
  - [ ] `test -f docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md || echo "STOP: still missing TASK template (write failure)"`
- [ ] list:
  - [ ] `ls -la docs/ops/meta | rg "DETERMINISTIC_" || true`

STOP condition here:
- created-but-missing persists (write failure / permission / path)

---

## 2) Create S18 skeleton docs from templates (no overwrite)
- [ ] set variables (path fixed):
  - `TPL_PLAN="docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md"`
  - `TPL_TASK="docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md"`
- [ ] ensure templates exist (if not, STOP per Phase 1.3 rule)
  - `test -f "$TPL_PLAN" || echo "STOP: missing $TPL_PLAN"`
  - `test -f "$TPL_TASK" || echo "STOP: missing $TPL_TASK"`
- [ ] create docs if missing:
  - [ ] `test -f docs/ops/S18_PLAN.md    || cp "$TPL_PLAN" docs/ops/S18_PLAN.md`
  - [ ] `test -f docs/ops/S18_TASK.md    || cp "$TPL_TASK" docs/ops/S18_TASK.md`
  - [ ] `test -f docs/ops/S18-00_PLAN.md || cp "$TPL_PLAN" docs/ops/S18-00_PLAN.md`
  - [ ] `test -f docs/ops/S18-00_TASK.md || cp "$TPL_TASK" docs/ops/S18-00_TASK.md`
- [ ] verify existence:
  - [ ] `ls -la docs/ops | rg "^.*S18" || true`

SKIP rule:
- if any target exists, do not overwrite; record 1-line SKIP in PR notes if needed

---

## 3) Scope Pin (edit contents now; prevent ex-post)
### 3.1 S18-00 scope statement (must match PLAN)
- [ ] In `docs/ops/S18-00_PLAN.md`, set Goal (1 sentence):
  - `Deterministic ops templates (v1) を導入し、以後の全フェーズのPlan/Task生成を決定論に固定する。`
- [ ] Ensure Deliverables list includes EXACT paths (6):
  - docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md
  - docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md
  - docs/ops/S18_PLAN.md
  - docs/ops/S18_TASK.md
  - docs/ops/S18-00_PLAN.md
  - docs/ops/S18-00_TASK.md

### 3.2 S18 epic minimal header (future phases blocked until defined)
- [ ] In `docs/ops/S18_PLAN.md`, write minimal:
  - `S18-00: Template kit bootstrap (this PR)`
  - `S18-01+: TBD (must be defined in ops docs before starting)`

STOP rule:
- If scope text diverges from this TASK, fix the docs now (no ambiguity)

---

## 4) Local Gates (quality gate; stop if fails)
- [ ] `make test`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [ ] if fail:
  - [ ] capture failing output (log path or pasted snippet)
  - [ ] fix
  - [ ] re-run gates

---

## 5) Canonical Pin (single for this PR)
- [ ] Decide Canonical = THIS PR's result only (Observations are not Canonical)
- [ ] Record:
  - [ ] Commit SHA (after commit)
  - [ ] Review Bundle filename
  - [ ] SHA256

---

## 6) Commit (docs-only)
- [ ] stage:
  - `git add docs/ops/meta docs/ops/S18*`
- [ ] confirm:
  - `git diff --cached --stat`
- [ ] commit:
  - `git commit -m "chore(ops): bootstrap deterministic templates v1 + kickoff S18-00"`
- [ ] status:
  - `git status -sb`

---

## 7) Push / PR
- [ ] push:
  - `git push -u origin HEAD`
- [ ] PR:
  - `gh pr create --fill`
- [ ] PR body includes Canonical block EXACTLY once:
  - Commit: `________`
  - Review Bundle: `review_bundle_YYYYMMDD_HHMMSS.tar.gz`
  - SHA256: `________`
  - Note: Future verify-only outputs are Observations (no Canonical update)
