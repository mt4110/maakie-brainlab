# S15-06: AI Work v2 (record/replay) — Plan

## Goal
AIレーンの実行を record / replay / verify-only として定義し、
CIは replay + verify-only で回る。
ローカルは record で成果物を固定できる。
成果物が spec_hash で決定し、同一Specなら replay出力が常に同一 になる。

## Observed Invariants (不変条件)
- 同一Spec → 同一 spec_hash
- verify-only は 生成しない（読み取り・整合性検証のみ）
- 成果物格納先は spec_hash で決まり、パスが揺れない
- evidenceは **「何を / どのモード / どのhash / 結果」**を必ず残す
- secrets/個人情報が混ざらない（evidenceは要点、全文・生ログを貼らない）

## Phase 1: 編集対象(確定) — File Set Pinning (Audit-Ready)

### Discovery Method
- Sources: `git diff --name-only origin/main...HEAD`, `rg -l ...`
- Filters: Excluded `.git/`, `.local/`, `target/`, etc.

### A. AI Lane Core
- [eval/run_eval.py](file:///Users/takemuramasaki/dev/maakie-brainlab/eval/run_eval.py) (includes WorkSpec, spec_hash, and modes)

### B. Providers
- [eval/run_eval.py](file:///Users/takemuramasaki/dev/maakie-brainlab/eval/run_eval.py) (includes Mock provider)

### C. Storage Layout / Hashing
- [eval/run_eval.py](file:///Users/takemuramasaki/dev/maakie-brainlab/eval/run_eval.py) (Layout: `.local/aiwork/<spec_hash>/`)

### D. CLI / Entrypoints
- [eval/run_eval.py](file:///Users/takemuramasaki/dev/maakie-brainlab/eval/run_eval.py) (--mode {record,replay,verify-only})

### E. Make / Scripts
- [Makefile](file:///Users/takemuramasaki/dev/maakie-brainlab/Makefile) (ai-smoke, ai-verify)

### F. CI Workflows
- [.github/workflows/verify_pack.yml](file:///Users/takemuramasaki/dev/maakie-brainlab/.github/workflows/verify_pack.yml)

### G. Ops Docs / Evidence Rails
- [docs/ops/S15-06_PLAN.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15-06_PLAN.md)
- [docs/ops/S15-06_TASK.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15-06_TASK.md)
- [docs/ops/S15-06_ACCEPTANCE.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15-06_ACCEPTANCE.md)

### I. Tests
- [tests/test_eval_artifacts_determinism.py](file:///Users/takemuramasaki/dev/maakie-brainlab/tests/test_eval_artifacts_determinism.py)

---

## Phase 2: Implementation Details
- `WorkSpec`: JSON containing question, model, provider, and type.
- `spec_hash`: SHA256 of canonicalized WorkSpec.
- Storage: `.local/aiwork/<spec_hash>/{spec.json, result.json}`.

## Phase 3: Verification
- `make ai-smoke`: Record with mock provider.
- `make ai-verify`: Verify-only (replay) with mock provider.
- CI: Run `make ai-verify` to ensure no network dependence.
