# S28-01-S28-10 THREAD v4 TASK — Context-Aware Readiness Hardening

Last Updated: 2026-02-27

## Progress

- S28-01-S28-10 v4: 100% (実装・テスト・S28一気通貫実行・`verify-il`・`ci-self`・PR反映まで完了)

## Current Facts

- v4実行結果: `S28-09=WARN_ONLY` (`SOFT_SLO_WARN`), `S28-10=PASS`。
- `waived_hard_count=4`（`SKIP_RATE_ENV_GAP`, `UNKNOWN_RATIO_WITH_ACTIONS`, `NOTIFY_NOT_ATTEMPTED`, `RELIABILITY_ENV_GAP`）。
- hard判定は0件となり、運用未接続起因の過検知を分離できている。

## Non-negotiables

- Ritual `22-16-22-99` を遵守（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking のまま。
- `STATUS.md` を進捗SOTに使わない（TASK + PR bodyに固定）。
- PR作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行して全green確認。
- 小分けPRを増やさず、1本でレビュー可能な状態までまとめる。

## Exit Conditions (v4)

- `s28_slo_readiness_v2_latest.json` が以下を満たす:
  - `slo.waived_hard_violations` に緩和根拠を保持
  - hard violation が0件、または真の障害のみ残存
  - `summary.readiness != BLOCKED`（運用未接続起因の過検知解消）
- `s28_closeout` が `waived_hard_count` を反映し、unresolved riskへ記録
- 対象ユニットテストが全green

## Checklist (Detailed)

### 0. Kickoff / Planning

- [x] 0-1. v4 PLAN を新規作成（逆算設計を固定）
- [x] 0-2. v4 TASK を新規作成（stopless手順を固定）
- [x] 0-3. S28-09 hard violations の根本原因を分類（品質劣化/環境未接続）

### 1. S28-01 Provider Canary Recovery

- [x] 1-1. `env_skip_runs/env_skip_rate` 算出関数を追加
- [x] 1-2. `SKIP_RATE_HIGH_ENV_GAP` reason code を追加
- [x] 1-3. payload `trend` / `summary` に env-gap signal を出力
- [x] 1-4. 生成artifactを再作成して値確認

### 2. S28-03 Readiness Notify

- [x] 2-1. `compute_delivery_rate` を追加（未試行は `null`）
- [x] 2-2. `delivery_state` (`SENT/FAILED/NOT_ATTEMPTED`) を追加
- [x] 2-3. payload `notification` に配信状態を固定
- [x] 2-4. dry-run時の挙動確認（未試行と失敗が混同されない）

### 3. S28-06 Reliability Soak

- [x] 3-1. `env_gap_profile` を追加
- [x] 3-2. `REASON_SKIP_RATE_HIGH_ENV_GAP` を判定分岐に追加
- [x] 3-3. payload `metrics` に env-gap比率を追加
- [x] 3-4. history入力で env-gap判定の整合を確認

### 4. S28-09 SLO Readiness (Core)

- [x] 4-1. waiver code 定数群を追加
- [x] 4-2. `build_waiver_context` を追加
- [x] 4-3. `apply_metric_waivers` を追加（hard -> soft変換）
- [x] 4-4. CLI引数追加（waiver閾値制御 / disableスイッチ）
- [x] 4-5. payloadに `waived_hard_violations` と `waiver_context` を出力
- [x] 4-6. summaryに `waived_hard_count` を出力
- [x] 4-7. v3サンプル入力で readiness判定の差分を確認

### 5. S28-10 Closeout

- [x] 5-1. waiver項目を unresolved risk導出へ統合
- [x] 5-2. `summary.waived_hard_count` を出力
- [x] 5-3. closeout artifactで反映確認

### 6. Tests (Precision)

- [x] 6-1. `test_s28_provider_canary_recovery.py` を更新
- [x] 6-2. `test_s28_readiness_notify.py` を更新
- [x] 6-3. `test_s28_reliability_soak_v2.py` を更新
- [x] 6-4. `test_s28_slo_readiness_v2.py` を更新
- [x] 6-5. `test_s28_closeout.py` を更新
- [x] 6-6. 上記テストを実行して全green確認

### 7. One-pass Validation Run

- [x] 7-1. `make ops-now`
- [x] 7-2. S28-01..S28-10 を順次実行（artifact再生成）
- [x] 7-3. S28-09/S28-10 のsummaryを確認
- [x] 7-4. 変更ファイルの最終レビュー（フォーマット・契約整合）

### 8. Ship Readiness

- [x] 8-1. `make verify-il`
- [x] 8-2. `ci-self up --ref "$(git branch --show-current)"` 事前条件を確認
- [x] 8-3. PR bodyへコマンド結果・readiness差分を記録可能な形に整理

## Validation Commands

- `python3 -m unittest -v tests/test_s28_provider_canary_recovery.py`
- `python3 -m unittest -v tests/test_s28_readiness_notify.py`
- `python3 -m unittest -v tests/test_s28_reliability_soak_v2.py`
- `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`
- `python3 -m unittest -v tests/test_s28_closeout.py`
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

## Notes for Single-PR Strategy

- v4は判定ロジックと根拠出力を同時に更新するため、分割PRより1PRの方が整合性レビューが容易。
- 変更範囲をS28関連スクリプトと対応テストへ限定し、GitHub API消費を抑える。
