# S28-01-S28-10 THREAD v4 PLAN — Context-Aware Readiness Hardening

Last Updated: 2026-02-27

## Goal

- S28-01..S28-10 を「一気通貫」で更新し、`BLOCKED` 判定の過検知を抑えつつ、実障害は確実に `BLOCKED` のまま検出する。
- 運用未接続（provider env未設定 / notify未送信）の状態を「品質劣化」と混同しない判定層を追加する。
- 1回の実装で PLAN/DO/CHECK を通し、PRの分割回数を増やさずにレビュー可能な品質へ到達させる。

## Current Point (2026-02-27)

- Branch: `ops/S28-01-S28-10`
- Latest readiness: `BLOCKED` (`HARD_SLO_VIOLATION`)
- Hard violations (v3):
  - `skip_rate`
  - `unknown_ratio`
  - `notify_delivery_rate`
  - `reliability_total_runs`
- Root pattern:
  - canary history が `MISSING_PROVIDER_ENV` 由来の `SKIP` に偏る
  - readiness notify が dry-run で配信未試行

## Problem Definition

- v3 はメトリクス閾値の厳密性は高いが、実行コンテキスト（接続済み/未接続）を区別しない。
- このため、実害のある劣化と環境準備不足が同じ hard violation として扱われる。
- 結果として closeout が `FAIL` 固定に寄り、改善の進捗が判定に反映されにくい。

## v4 Design Principles

- Hard block は「即時是正が必要な品質劣化」に限定する。
- 緩和（waiver）は暗黙に行わず、artifactに根拠（`waiver_code`, `waiver_note`）を必ず残す。
- 閾値を単純に緩めるのではなく、根拠条件を満たす場合のみ hard -> soft へ変換する。
- 判定ロジックは deterministic にし、同一入力で常に同一結果を返す。

## Completion Definition (v4 Exit)

- S28-09:
  - hard violations が「真の品質劣化」のみ残る
  - 緩和された項目は `slo.waived_hard_violations` に列挙される
  - readiness が `BLOCKED` 以外（`WARN_ONLY` または `READY`）を再現可能
- S28-10:
  - closeout が waiver情報を保持し、`unresolved_risks` に運用上の残リスクを記録
- Unit tests:
  - 新規ロジック（env-gap判定、delivery状態、waiver変換）を網羅

## Backward Design (S28-10 -> S28-01)

### S28-10 Closeout v4

- `s28_closeout.py` に waiver由来の残リスク記録を追加する。
- `summary.waived_hard_count` を出力し、判定の透明性を確保する。

### S28-09 SLO Readiness v4

- `s28_slo_readiness_v2.py` に context-aware waiver engine を追加する。
- hard violation を以下条件で soft へ変換する:
  - `skip_rate`: provider env gapが支配的
  - `notify_delivery_rate`: notifyが未試行（dry-run / webhook未設定）
  - `reliability_total_runs`: env gapで走行不足
  - `unknown_ratio`: taxonomy feedbackが有効で候補蓄積が閾値以上
- 変換結果を `waived_hard_violations` と `waiver_context` に固定する。

### S28-08 Evidence Trend Index v3 (No schema bump)

- ステータス集約は現行維持。
- S28-09の出力改善により、S28-08->S28-09の解釈に一貫性を持たせる。

### S28-07 Acceptance Wall v3 (No schema bump)

- 受入判定ロジックは維持。
- v4ではS28-09判定透明性をテスト層で担保するため、S28-07仕様には影響を与えない。

### S28-06 Reliability Soak v2+

- `env_gap_profile` を追加し、`env_gap_runs/env_gap_ratio` を出力する。
- `skip_rate` 高騰がenv gap起因なら `REASON_SKIP_RATE_HIGH_ENV_GAP` を返せるようにする。

### S28-05 Policy Drift Guard v2 (No logic change)

- ドリフト検知仕様は維持（v4の焦点外）。

### S28-04 Incident Triage Pack v2 (No logic change)

- triage集約仕様は維持（入力品質が向上する前提）。

### S28-03 Readiness Notify v2+

- 配信状態を `SENT/FAILED/NOT_ATTEMPTED` へ分離し、`delivery_rate` を明示する。
- 未試行時の `delivery_rate` は `null` とし、SLO側で誤検知を避ける。

### S28-02 Taxonomy Feedback Loop v2 (No schema bump)

- 既存の `candidate_count/collection_actions` をSLO waiver判定の根拠として使用する。

### S28-01 Provider Canary Recovery v2+

- `env_skip_runs/env_skip_rate` を追加して、env gap支配を数値化する。
- `SKIP_RATE_HIGH_ENV_GAP` を導入し、skip高騰の理由を分離する。

## Planned Impacted Files

- `docs/ops/S28-01-S28-10-THREAD-V4_PLAN.md`
- `docs/ops/S28-01-S28-10-THREAD-V4_TASK.md`
- `scripts/ops/s28_provider_canary_recovery.py`
- `scripts/ops/s28_readiness_notify.py`
- `scripts/ops/s28_reliability_soak_v2.py`
- `scripts/ops/s28_slo_readiness_v2.py`
- `scripts/ops/s28_closeout.py`
- `tests/test_s28_provider_canary_recovery.py`
- `tests/test_s28_readiness_notify.py`
- `tests/test_s28_reliability_soak_v2.py`
- `tests/test_s28_slo_readiness_v2.py`
- `tests/test_s28_closeout.py`

## Validation Strategy

軽量（ローカル即時）:

- `make ops-now`
- `python3 -m unittest -v tests/test_s28_provider_canary_recovery.py`
- `python3 -m unittest -v tests/test_s28_readiness_notify.py`
- `python3 -m unittest -v tests/test_s28_reliability_soak_v2.py`
- `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`
- `python3 -m unittest -v tests/test_s28_closeout.py`

中量（S28一気通貫）:

- `make s28-provider-canary-recovery`
- `make s28-taxonomy-feedback-loop`
- `make s28-readiness-notify`
- `make s28-incident-triage-pack-v2`
- `make s28-policy-drift-guard-v2`
- `make s28-reliability-soak-v2`
- `make s28-acceptance-wall-v3`
- `make s28-evidence-trend-index-v3`
- `make s28-slo-readiness-v2`
- `make s28-closeout`

重量（ship直前）:

- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Risks and Mitigations

- リスク: waiver条件が広すぎると本来の障害を見逃す。
- 対策: waiverは metricごとに限定条件を定義し、`waiver_code` をartifact化。

- リスク: unknown_ratio緩和が過剰になる。
- 対策: `taxonomy_waiver_min_candidates` と `taxonomy_waiver_max_unknown` の二重条件に限定。

- リスク: notify未試行が恒常化する。
- 対策: `NOT_ATTEMPTED` をsoft化しても closeout risk に必ず残す。

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  define context-aware hard/soft split and artifact contract
DO:
  implement env-gap/delivery-state signals + SLO waiver engine + closeout reflection
CHECK:
  run unit tests -> run S28 chain -> inspect readiness/closeout artifacts
SHIP:
  keep single cohesive change set, record commands and results in PR body
```
