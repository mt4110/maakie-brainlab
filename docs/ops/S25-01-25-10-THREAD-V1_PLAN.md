# S25-01-25-10 THREAD v1 PLAN — Current-Point Ops + ML/RAG/LangChain Backward Design

Last Updated: 2026-02-26

## Goal

- 「今どこを走っているか」を 10 秒で判断できる運用導線を作る。
- S25-10 時点で、テスト運用・ML実験・RAG調整・LangChain接続の最小一周が再現可能になる。

## Background

- 現在の実装資産は S24 thread（CI/運用最適化）が中心で、S25 の全体図と実行タスクが未固定。
- 「現在地」がブランチ名・ドキュメント・手元メモに分散すると、実装順序と完了条件が曖昧になる。
- 次フェーズでは、実装だけでなく「どこまでで完成か」を逆算で先に固定する必要がある。

## Constraints (Non-negotiable)

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone 系は non-blocking 契約を維持する（blocking gateを増やさない）。
- `docs/ops/STATUS.md` を進捗の source of truth にしない。進捗は TASK/PR body に記録する。
- stopless 運用（`OK:/WARN:/ERROR:/SKIP:`）を維持し、隠れた停止条件を作らない。

## Non-Goals

- 本スレッドで「最強モデル」を作り切ること。
- 本スレッドで SaaS 本番運用へ直接投入すること。
- 既存 S24 以前の運用契約を破壊する大規模リライト。

## S25 Completion Definition (S25-10 Exit)

- 現在地表示コマンドで `branch / task / progress / next actions` が即時に出る。
- テスト導線が 3 層（smoke / regression / acceptance）で固定される。
- ML実験（最小1系統）と RAG調整（最小1ループ）を実施し、結果を再現できる。
- LangChain 接続の PoC を 1 本通し、失敗時の切戻し経路を持つ。

## Success Metrics

- 現在地確認の手順を `1コマンド` に集約（暗黙手順ゼロ）。
- TASK のチェック項目完了率と Progress 行の齟齬をゼロにする。
- RAG/ML/LangChain の評価記録を最低 1 回ずつ PR body に固定する。
- S25 closeout で required checks 破壊インシデント 0 件。

## Backward Phase Design (S25-10 -> S25-01)

### S25-10 Closeout

- Before/After（品質・速度・運用負荷）を PR body に固定。
- 未解決リスクと次スレッド handoff を明記。

### S25-09 LangChain PoC

- 既存パイプラインとの接続点を明示し、最小フローを通す。
- 契約外挙動が出た場合の rollback 手順を 1 つ固定。

### S25-08 RAG Tuning Loop

- パラメータ変更 -> eval -> 判定 を最小1ループ運用する。
- 「改善/悪化」を JSONL evidence で比較できる状態を作る。

### S25-07 ML Experiment Loop

- 学習/推論の実験テンプレートを固定（入力・出力・評価軸を明記）。
- run 差分を再現できるよう seed/設定を記録する。

### S25-06 Acceptance Test Wall

- 完成判定の acceptance cases を固定し、回帰時に即検知できるようにする。

### S25-05 Regression Safety

- 既存 `make verify-il` 系列に追加検証を差し込み、壊してはいけない契約を明示する。

### S25-04 Observability

- 実験と実装の観測ログ保存先を固定し、探索コストを削減する。

### S25-03 Baseline Freeze

- 変更前 baseline（テスト結果/評価値/主要コスト）を記録し、比較基準を凍結する。

### S25-02 Work Breakdown

- 具体タスクを PLAN から TASK へ分解し、実装順序を固定する。

### S25-01 Current-Point Contract

- 「現在地」の定義（branch, task file, progress, unchecked top items）を固定する。
- `ops-now` コマンド導線を整備する。

## Planned Impacted Files

- `docs/ops/S25-01-25-10-THREAD-V1_PLAN.md`
- `docs/ops/S25-01-25-10-THREAD-V1_TASK.md`
- `docs/ops/S25-02_WORK_BREAKDOWN.md`
- `scripts/ops/obs_contract.py`
- `scripts/ops/s25_obs_pr_summary.py`
- `scripts/ops/s25_regression_safety.py`
- `scripts/ops/s25_acceptance_wall.py`
- `docs/ops/S25-06_ACCEPTANCE_CASES.json`
- `scripts/ops/s25_ml_experiment.py`
- `docs/ops/S25-07_ML_EXPERIMENT_TEMPLATE.json`
- `docs/ops/S25-04_OBSERVABILITY_CONTRACT.md`
- `docs/evidence/s25-04/*`
- `docs/evidence/s25-05/*`
- `docs/evidence/s25-06/*`
- `docs/evidence/s25-07/*`
- `scripts/ops/current_point.py`
- `Makefile`
- `docs/ops/ROADMAP.md`

## Validation Strategy

- 軽量:
  - `python3 scripts/ops/current_point.py`
  - `python3 -m unittest -v tests/test_il_entry_smoke.py`
- 中量:
  - `make verify-il-thread-v2`
- 重量（ship前）:
  - `make verify-il`
  - `source /path/to/your/nix/profile.d/nix-daemon.sh`
  - `ci-self up --ref "$(git branch --show-current)"`

## Risks and Mitigations

- リスク: 現在地表示が命名揺れで誤判定する。
- 対策: ブランチ名と TASK 名を複数パターンで解決し、未解決時は WARN で次アクションを表示する。

- リスク: ML/RAG/LangChain を同時並行で触って評価が混線する。
- 対策: Baseline 固定 -> 1系統ずつ変更 -> evidence記録 の順序を厳守する。

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  define S25-10 completion and backward phases
DO:
  implement current-point command + docs/task structure
CHECK:
  run lightweight checks, then verify-il gates
SHIP:
  commit small, update PR body with command/result facts
```
