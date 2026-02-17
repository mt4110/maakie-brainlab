# S20-08: Python Env Canonicalization (Task)

## Progress
- S20-08: 6% (Kickoff + verify-only evidence done; canonicalization not yet)

## Task (Order is Deterministic)

### 0) Safety Snapshot (軽量・落ちない)
- [ ] Print repo root + status (manual read)
  - Command:
    - `bash -lc 'ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; if [ -n "$ROOT" ]; then cd "$ROOT"; pwd; git status -sb; else echo "ERROR: not in git repo"; fi'`
- [ ] Inventory current python wiring (no changes)
  - `bash -lc 'ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; if [ -n "$ROOT" ]; then cd "$ROOT"; rg -n "requirements.txt|python -m venv|\\.venv/bin/python|setup-python" Makefile .github/workflows docs/ops || true; else echo "ERROR: not in git repo"; fi'`

### 1) Decide the Single Path (設計決定)
- [ ] Decide `requirements.txt` policy (choose ONE and write it into S20-08_PLAN.md)
  - Option 1: remove requirements.txt, unify on `pyproject.toml + uv.lock`
  - Option 2: keep requirements.txt as generated artifact from lock (rule fixed)

### 2) Implement Canonical Bootstrap (小刻み)
- [ ] Update `Makefile` to enforce canonical python: `./.venv/bin/python`
  - Rules:
    - python 実行は `.venv/bin/python` のみ
    - bootstrap 手順は 1 本にする（CI と同型）
    - 重い処理は 1 ターゲット 1 コマンドに分割
- [ ] (Optional) Add `scripts/py_env_report.py` (MUST: never crash; only print)
  - Output contract:
    - `OK:` / `WARN:` / `ERROR:` lines only
    - no `sys.exit`, no uncaught exception

### 3) Align GitHub Workflows (CI/Local 同型)
- [ ] Update workflows to match the chosen single path:
  - `.github/workflows/test.yml`
  - `.github/workflows/eval_run.yml`
  - `.github/workflows/eval_strict.yml`
  - `.github/workflows/verify_pack.yml`
- [ ] Ensure they create `.venv` and run tests using `.venv/bin/python`

### 4) Docs (運用固定)
- [ ] Add `docs/ops/PYTHON_ENV.md`
  - What to do:
    - bootstrap
    - run tests
    - “混線したときの観測” (`scripts/py_env_report.py` の使い方)
  - What NOT to do:
    - `pip --user`
    - system python で repo タスク実行

### 5) Verification (儀式・ただし重い処理は分割)
- [ ] Delete `.venv` (local) then run canonical bootstrap (timebox)
- [ ] `make test` PASS
- [ ] `git status -sb` clean
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

### 6) Evidence + PR
- [ ] Capture latest `.local/prverify/prverify_*.md` into `docs/evidence/prverify/`
- [ ] Create PR body in SOT/証拠スタイル（ガチガチ版 + 短い版併記）
