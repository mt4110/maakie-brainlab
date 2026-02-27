# S22-05 TASK — P6 IL Entry Single Entry + Always Verify

## 0) Branch (No exit)
- [x] `git switch main 2>/dev/null || true`
- [x] `git pull --ff-only 2>/dev/null || true`
- [x] `git switch s22-05-il-entry-unify-always-verify-v1 2>/dev/null || git switch -c s22-05-il-entry-unify-always-verify-v1 2>/dev/null || true`
- [x] `git status -sb 2>/dev/null || true`

## 1) Observe (Light)
- [x] `ls -la src/il_validator.py src/il_executor.py scripts/il_exec_run.py 2>/dev/null || true`
- [x] `rg -n "def execute_il|class ILValidator|class ILCanonicalizer" src scripts tests 2>/dev/null || true`

## 2) Add Contract Docs (Light)
- [x] Create `docs/il/IL_ENTRY_CONTRACT_v1.md`
  - [x] 入力: IL json path / out_dir / fixture_db_path(optional)
  - [x] 出力: report.json + logs (OK/ERROR/SKIP)
  - [x] 失敗規約: STOP=1 → 後続SKIP、exit無し
  - [x] canonicalize規約: src/il_validator に委譲（入口で勝手に増やさない）

## 3) Implement Single Entry (Core)
- [x] Create `scripts/il_entry.py`
  - [x] import は既存へ寄せる（validator/canonicalizer/executor を再実装しない）
  - [x] try/catch で全体を包み、例外は必ず `ERROR:` で回収（落ちない）
  - [x] validate/canonicalize → execute_il → artifacts verify を固定順
  - [x] artifacts verify（軽量）:
    - [x] out_dir が存在
    - [x] report.json（または既存 report 形式）が書かれた/存在
    - [x] 必須キー最低限（例: ok/status/opcode_count 等）※増やしすぎない

## 4) Add Smoke Script (Fast, Stopless)
- [x] Create `scripts/il_entry_smoke.py`
  - [x] good IL fixture を最小で1つ（既存fixturesがあればそれを使う）
  - [x] bad IL fixture を最小で1つ（schema違反/予約語/型違い）
  - [x] 実行して `OK:` / `ERROR:` を出す（例外で止めない）
  - [x] 最後に summary 1行（OK=.. ERROR=.. SKIP=..）

## 5) Runbook (Ops)
- [x] Create `docs/ops/IL_ENTRY_RUNBOOK.md`
  - [x] “普段”: smoke のみ（速い）
  - [x] “最後”: heavy verify-only（遅い、別ステップ）

## 6) Verification (Split: light then heavy)
### 6-A) Light
- [x] `mkdir -p .local/obs 2>/dev/null || true`
- [x] `python3 scripts/il_entry_smoke.py 2>&1 | tee .local/obs/il_entry_smoke.log || true`
- [x] `rg -n "^ERROR:" .local/obs/il_entry_smoke.log 2>/dev/null || true`
- [x] `rg -n "^OK:"    .local/obs/il_entry_smoke.log 2>/dev/null || true`

### 6-B) Heavy (Optional at end)
- [x] `make test 2>&1 | tee .local/obs/make_test.log || true`
- [x] `rg -n "^FAIL|FAILED|ERROR:" .local/obs/make_test.log 2>/dev/null || true`
- [x] `go run ./cmd/reviewpack/main.go submit --mode verify-only 2>&1 | tee .local/obs/reviewpack_verify_only.log || true`
- [x] `rg -n "PASS|OK:|ERROR:" .local/obs/reviewpack_verify_only.log 2>/dev/null || true`

## 7) Commit Plan (1 PRで完結)
- [x] commit1: docs(il): add IL_ENTRY_CONTRACT_v1
- [x] commit2: feat(il): add scripts/il_entry.py (single entry)
- [x] commit3: test(il): add scripts/il_entry_smoke.py
- [x] commit4: docs(ops): add IL_ENTRY_RUNBOOK + wiring notes

## 8) PR
- [x] Title: `S22-05: IL entry single entry + always verify`
- [x] Milestone: `S22-05`
- [x] Body: SOT/証拠スタイル（テンプレ使用）
