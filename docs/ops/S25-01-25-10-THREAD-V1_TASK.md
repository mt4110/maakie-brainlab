# S25-01-25-10 THREAD v1 TASK — Current-Point Ops + ML/RAG/LangChain Backward Design

Last Updated: 2026-02-27

## Progress

- S25-01-25-10: 100% (S25-01..S25-10 完了)

## Ritual 22-16-22-99

- PLAN: `docs/ops/S25-01-25-10-THREAD-V1_PLAN.md`
- DO: 下記チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: 小分けコミット + PR body に結果固定

## Current-Point Rule (SOT)

- 現在地は `branch + TASK progress + checklist未完了先頭` の3点で定義する。
- 進捗の source of truth は本 TASK と PR body（`STATUS.md` には依存しない）。
- 毎作業開始時に `make ops-now` を実行し、同じ形式で確認する。

## Checklist

### S25-01 Current Point Contract

- [x] S25 thread の PLAN/TASK を新規作成
- [x] `make ops-now` 導線を追加
- [x] branch/task/progress/next actions が表示されることを確認

### S25-02 Work Breakdown

- [x] 実装タスクを phase 単位で PR 粒度へ分割
- [x] 依存関係（先行/後続）を明示
  - matrix: `docs/ops/S25-02_WORK_BREAKDOWN.md`

### S25-03 Baseline Freeze

- [x] 変更前のテスト/eval baseline を PR body に固定
- [x] 比較指標（品質/速度/コスト）を固定
  - baseline artifact: `docs/evidence/s25-03/baseline_latest.json`
  - snippet artifact: `docs/evidence/s25-03/baseline_latest.md`

### S25-04 Observability

- [x] 実験ログの出力先を固定
- [x] `OK:/WARN:/ERROR:/SKIP:` 形式で観測結果を統一
- [x] PR本文へ貼る観測サマリを自動生成
  - contract helper: `scripts/ops/obs_contract.py`
  - summary generator: `scripts/ops/s25_obs_pr_summary.py`
  - contract doc: `docs/ops/S25-04_OBSERVABILITY_CONTRACT.md`
  - summary artifact: `docs/evidence/s25-04/observability_latest.md`

### S25-05 Regression Safety

- [x] 既存 verify コマンドとの整合を確認
- [x] 既存契約を壊す変更がないことを明示
  - runner: `scripts/ops/s25_regression_safety.py`
  - artifact: `docs/evidence/s25-05/regression_safety_latest.md`
  - gate: `make s25-regression-safety`

### S25-06 Acceptance Test Wall

- [x] acceptance cases を最小セットで定義
- [x] pass/fail 判定条件を明記
  - cases: `docs/ops/S25-06_ACCEPTANCE_CASES.json`
  - runner: `scripts/ops/s25_acceptance_wall.py`
  - artifact: `docs/evidence/s25-06/acceptance_wall_latest.md`
  - gate: `make s25-acceptance-wall`

### S25-07 ML Experiment Loop

- [x] ML 実験テンプレート（入力/出力/評価）を固定
- [x] seed と設定を保存し再実行可能にする
  - template: `docs/ops/S25-07_ML_EXPERIMENT_TEMPLATE.json`
  - runner: `scripts/ops/s25_ml_experiment.py`
  - artifact: `docs/evidence/s25-07/ml_experiment_latest.md`
  - gate: `make s25-ml-experiment`

### S25-08 RAG Tuning Loop

- [x] RAG パラメータ調整を 1 ループ実行
- [x] baseline 比較の evidence を保存
  - tuning SOT (TOML): `docs/ops/S25-08_RAG_TUNING.toml`
  - runner: `scripts/ops/s25_rag_tuning_loop.py`
  - artifact: `docs/evidence/s25-08/rag_tuning_latest.md`
  - gate: `make s25-rag-tuning`
  - storage policy: `SOT=TOML / Evidence=JSON / SearchDB=SQLite`
  - docker compose: `docker-compose.yml` (PostgreSQL example is commented out)

### S25-09 LangChain PoC

- [x] 最小接続フローを実装
- [x] rollback 手順を記述

### S25-10 Closeout

- [x] Before/After 比較を PR body に固定
- [x] 未解決リスクと次スレ handoff を記載
- [x] closeout コミットを作成

## Validation Commands

軽量（毎PR）:

- [x] `python3 scripts/ops/current_point.py`
- [x] `python3 tests/test_il_entry_smoke.py`

中量（必要時）:

- [x] `make verify-il-thread-v2`

重量（ship前）:

- [x] `make verify-il`
- [x] `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [ ] `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は PR body に固定する。
- 各 phase で最低1行の `OK:/ERROR:/SKIP:` を残す。
- `SKIP` は理由を1行で明示する。
