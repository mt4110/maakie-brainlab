# S20-08: Python Env Canonicalization (Plan)

## SOT
- Objective:
  - Python 実行系の混線（.venv / system python / pip --user）を長期で破綻しない形に一本化する。
- Canonical Decision (MUST):
  - Canonical interpreter: `./.venv/bin/python`
  - Canonical env location: repo root `./.venv/`
  - Canonical dependency install: **single path** (CI/Local 共通)
  - Prohibit (Ops):
    - `pip --user` を運用から排除（.venv を迂回して混線の原因になる）
    - system python で repo タスクを実行しない（bootstrap の最初だけは例外になり得る）
- Inputs (files):
  - `Makefile`
  - `pyproject.toml`
  - `uv.lock` (exists)
  - `.github/workflows/test.yml`
  - `.github/workflows/eval_run.yml`
  - `.github/workflows/eval_strict.yml`
  - `.github/workflows/verify_pack.yml`
  - `docs/ops/README.md`
  - (legacy) `requirements.txt` (扱いを決める)
- Deliverables:
  - Docs:
    - `docs/ops/S20-08_PLAN.md` / `docs/ops/S20-08_TASK.md` (this phase)
    - `docs/ops/PYTHON_ENV.md` (canonical 手順と禁止事項)
  - Implementation:
    - `Makefile`: python 実行を `.venv/bin/python` に固定し、bootstrap を単一路線へ
    - GitHub Workflows: venv 作成・依存導入を単一路線へ（ローカルと同型）
    - (Optional guardrail) `scripts/py_env_report.py`:
      - 現在の python 実体 / venv 判定 / pip user 設定を **落ちずに**表示する
- Gates:
  - `make test` PASS
  - `go run cmd/reviewpack/main.go submit --mode verify-only` PASS (clean tree 前提)
- Evidence Baseline:
  - Kickoff commit: `1ffd898` (docs kickoff)
  - verify-only bundle: `review_bundle_20260217_190015.tar.gz` (SHA256: 51422fb7...)

## Problem Statement
- 現状: `.venv` がある一方で、CI は `requirements.txt` 由来、ローカル bootstrap は `pyproject.toml` 由来、さらに `pip --user` が混入し得る。
- これにより:
  - “どの Python が真実か” が時間と人でブレる
  - 再現性が壊れ、デバッグが沼る

## Strategy (Deterministic)
### Phase A: Inventory (軽量)
- repo 内の python 導線を列挙（Makefile / workflows / docs）
- `requirements.txt` を「残す / 捨てる / 生成物にする」のどれかに確定する

### Phase B: Canonical Toolchain (一本化)
- Local/CI ともに「同じ導線」で `.venv` を作り、依存を入れる
- `.venv/bin/python` を唯一の実行点にする（Makefile から system python を追放）

### Phase C: Guardrails (落ちない観測)
- `scripts/py_env_report.py` を追加し、混線の兆候を **print** で出す
  - sys.executable
  - venv 判定（prefix / base_prefix）
  - pip user 設定（環境変数 / config 由来の有無）

### Phase D: Docs (運用に落とす)
- `docs/ops/PYTHON_ENV.md` に canonical 手順と禁止事項を明文化
- “困ったらこれを見る” を 1 箇所に固定

## Decision: requirements.txt の扱い
- Option 1 (推奨・単純): `requirements.txt` を廃止し、`pyproject.toml + uv.lock` に統一
  - Pros: 導線が 1 本、ブレない
  - Cons: 依存が重い場合 CI が遅くなる可能性
- Option 2 (妥協): `requirements.txt` は残すが、生成物として `uv.lock` から毎回生成（手順固定）
  - Pros: CI を軽くしやすい
  - Cons: “生成ルール” が第二の契約になる

このフェーズでは Option を確定し、以後は変更しない（変更は別フェーズ）。

## Acceptance Criteria
- Fresh 状態で:
  - `.venv` を消しても、定めた bootstrap 手順で復元できる
  - `make test` が `.venv/bin/python` で走る
  - CI が同じ導線で PASS
- `pip --user` 前提の手順が docs から消える
