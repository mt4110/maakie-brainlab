# S26-01-S26-04 THREAD v1 PLAN — Precision AI Orchestration Core

Last Updated: 2026-02-27

## Goal

- AIオーケストレーションの心臓部を、`失敗しても止まらない` 前提で精密化する。
- S26-04 Exit 時点で、provider canary / medium eval wall / rollback artifact を統合実行できる状態にする。

## Current Point (as of 2026-02-27)

- ブランチ: `ops/S26-01-S26-02`
- `make ops-now` は S26 TASK を参照し、進捗を可視化できる。
- S25 closeout で残した handoff 3件のうち、S26-01..03 が直結対象。

## Distance to Goal (Backward Estimate)

- S26-01 Provider Canary + Timeout/Retry Policy 固定: 30%
- S26-02 Medium Dataset Eval Wall 拡張: 30%
- S26-03 Rollback Artifact 常時収集: 20%
- S26-04 Orchestration Core 統合実行: 20%

## Background

- S25 で ML/RAG/LangChain の最小一周は完了したが、外部 provider 実接続の失敗モードが未評価。
- 既存 eval は seed-mini 中心で、ドメイン拡張時の揺れ検知力が不足。
- 「今どこか」と「なぜその順序か」を逆算で固定しないと、実装と評価が再び分離する。

## Constraints (Non-negotiable)

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking のまま維持する（blocking gate を増やさない）。
- `STATUS.md` を進捗 SOT にしない。進捗は本 TASK と PR body に固定する。
- stopless 運用（`OK:/WARN:/ERROR:/SKIP:`）を維持し、隠れ停止条件を入れない。

## Non-Goals

- 本スレッドで本番SaaS向け multi-region 可用性を完成させること。
- 本スレッドでモデル品質最適化を限界までやり切ること。
- 既存 S25 資産を全面リライトすること。

## Orchestration Core Design (Target Skeleton)

### Plane-A: Policy Plane（決める）

- Provider policy contract を TOML で固定:
  - `timeout_sec`, `max_retries`, `retry_backoff_ms`, `jitter_ms`
  - `retryable_reason_codes`, `non_retryable_reason_codes`
  - `circuit_open_sec`, `max_inflight`
- Policy hash を evidence に出し、実行結果と必ず紐づける。

### Plane-B: Execution Plane（動かす）

- `s26_provider_canary.py` で provider 実接続 canary を実行。
- `s26_medium_eval_wall.py` で dataset schema/distribution 契約を検証。
- `s26_rollback_artifact.py` で rollback 実演ログを収集。
- `s26_orchestration_core.py` で S26-01..03 を順序統合実行。

### Plane-C: Evidence Plane（証明する）

- canary 実行結果を `docs/evidence/s26-01/*` に JSON + Markdown で保存。
- medium dataset の評価結果を `docs/evidence/s26-02/*` に保存。
- rollback artifact を `docs/evidence/s26-03/*` に保存。
- orchestration core 集約結果を `docs/evidence/s26-04/*` に保存。
- PR body は command/result/delta/rollback を必須項目として固定。

## Backward Phase Design (S26-04 -> S26-01)

### S26-04 Orchestration Core

- S26-01..03 を順序実行し、stopless で統合結果を保存する。
- step 単位の rc/log/status を evidence 化し、異常を局所化する。

### S26-03 Rollback Artifact

- rollback command 実行ログを artifact として常時収集する。
- upstream（canary/eval wall）の状態と紐づけて監査可能にする。

### S26-02 Medium Eval Wall

- RAG/ML/LangChain 共通で使える medium dataset を作成。
- seed-mini 比較で、品質・速度・失敗 taxonomy の差分を常時観測する。
- dataset と閾値を固定し、再実行時の判定ぶれを抑制する。

### S26-01 Provider Canary

- provider 実接続 smoke を導入し、timeout/retry policy を契約化する。
- 失敗時は rollback 導線を 1 コマンドで実行可能にする。
- canary を `軽量（ローカル）` と `重量（ci-self）` に分離する。

### Closeout

- Before/After（品質・速度・運用負荷）を PR body に固定。
- unresolved risk と次スレ handoff を明記。

## S26 Completion Definition (S26-04 Exit)

- `make ops-now` が S26 TASK を参照し、進捗と次アクションを即時表示する。
- provider canary が timeout/retry policy 付きで再現可能。
- medium dataset 評価壁が RAG/ML/LangChain で共通運用できる。
- rollback artifact が常時収集される。
- orchestration core が S26-01..03 を統合実行できる。
- closeout evidence が PR body と整合し、残課題が明文化される。

## Planned Impacted Files

- `docs/ops/S26-01-S26-02-THREAD-V1_PLAN.md`
- `docs/ops/S26-01-S26-02-THREAD-V1_TASK.md`
- `docs/ops/S26-01_PROVIDER_CANARY.toml` (new)
- `docs/ops/S26-02_MEDIUM_EVAL_WALL.toml` (new)
- `scripts/ops/s26_provider_canary.py` (new)
- `scripts/ops/s26_medium_eval_wall.py` (new)
- `scripts/ops/s26_rollback_artifact.py` (new)
- `scripts/ops/s26_orchestration_core.py` (new)
- `data/eval/datasets/rag-eval-wall-v1__seed-medium__v0001/*` (new)
- `tests/test_s26_provider_canary.py` (new)
- `tests/test_s26_medium_eval_wall.py` (new)
- `tests/test_s26_rollback_artifact.py` (new)
- `tests/test_s26_orchestration_core.py` (new)
- `Makefile` (new targets)
- `docs/evidence/s26-01/*`
- `docs/evidence/s26-02/*`
- `docs/evidence/s26-03/*`
- `docs/evidence/s26-04/*`
- `docs/evidence/s26-closeout/*`

## Validation Strategy

- 軽量:
  - `make ops-now`
  - `python3 -m unittest -v tests/test_s26_provider_canary.py`
  - `python3 -m unittest -v tests/test_s26_medium_eval_wall.py`
  - `python3 -m unittest -v tests/test_s26_rollback_artifact.py`
  - `python3 -m unittest -v tests/test_s26_orchestration_core.py`
- 中量:
  - `make s26-provider-canary`
  - `make s26-medium-eval-wall`
  - `make s26-rollback-artifact`
  - `make s26-orchestration-core`
- 重量（ship前）:
  - `make verify-il`
  - `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
  - `ci-self up --ref "$(git branch --show-current)"`

## Risks and Mitigations

- リスク: provider 実接続は外部要因で flaky になる。
- 対策: timeout/retry/circuit-open を契約化し、`FAIL` と `SKIP` の判定基準を明示する。

- リスク: medium dataset 拡張で評価時間が肥大化する。
- 対策: lightweight と heavyweight を分離し、PR単位では lightweight を常用する。

- リスク: dataset 更新で比較軸が崩れる。
- 対策: dataset ID/version を固定し、差分更新時は new version を発行する。

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  freeze policy contract and medium-dataset acceptance
DO:
  implement provider canary, eval wall, rollback artifact, orchestration runner
CHECK:
  run lightweight -> medium -> heavyweight in order
SHIP:
  commit small, update PR body with command/result facts
```
