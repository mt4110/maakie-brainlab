# S28-01-S28-10 THREAD v3 PLAN — WARN_ONLY to READY Hardening

Last Updated: 2026-02-27

## Goal

- S28 v1 の成果を運用定着フェーズへ引き上げ、`WARN_ONLY` を `READY` へ収束させる。
- S28-10 Exit v2 時点で、`recovery -> feedback -> notify -> triage -> drift -> soak -> acceptance -> trend -> slo -> closeout` の全経路を「実送信あり」「継続運転あり」で再現可能にする。

## Current Point (as of 2026-02-27)

- ブランチ: `ops/S28-01-S28-10`
- 最新 SLO: `readiness=WARN_ONLY`, `reason_code=SOFT_SLO_WARN` (`docs/evidence/s28-09/slo_readiness_v2_latest.json`)
- 主要メトリクス:
  - `skip_rate=1.0`
  - `notify_delivery_rate=0.0`
  - `unknown_ratio=0.0625`
  - `acceptance_pass_rate=1.0`
- WARN 要因:
  - S28-01: `RECOVERY_REQUIRED`
  - S28-03: `NOTIFY_DRY_RUN`
  - S28-04: `TRIAGE_ALERT`
  - S28-05: `BASELINE_CREATED`
  - S28-06: `INSUFFICIENT_RUNS`

## Latest Execution Result (2026-02-27)

- S28-01..S28-08: 実行完了（artifact更新）
- S28-09: `BLOCKED` (`HARD_SLO_VIOLATION`)
- S28-10: `FAIL` (readiness=`BLOCKED`)
- 現在の主残課題:
  - provider env 未設定に起因する `skip_rate`/`total_runs` 不達
  - readiness 通知の実送信（dry-run脱却）

## Constraints (Non-negotiable)

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking のまま維持し、milestone必須 gate を増やさない。
- `docs/ops/STATUS.md` を進捗 SOT に使わない。進捗は TASK と PR body に固定する。
- PR 作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行し、全 green を確認してから進める。
- 禁止ブランチ `codex/feat*` を使わない。

## Completion Definition (S28-10 Exit v2)

- S28-09 の最終判定が `readiness=READY` になる。
- `skip_rate <= 0.20` かつ `notify_delivery_rate >= 0.95`。
- S28-06 で `total_runs >= 24`（単発観測から継続運転へ移行）。
- S28-05 で baseline 初回作成 WARN を解消し、drift判定が通常運用状態で回る。
- S28-10 closeout に Before/After・unresolved risk・S29 handoff を v2更新して固定する。

## Backward Phase Design (S28-10 -> S28-01)

### S28-10 Closeout v2

- v2 の改善値（skip率/通知配信率/連続稼働件数）を closeout artifact に固定する。
- unresolved risk を「残課題」「監視で許容」の2層で整理し、S29 handoff を具体化する。

### S28-09 SLO Readiness v3

- `notify_delivery_rate` と `skip_rate` の閾値を運用実態に合わせて再定義する。
- `WARN_ONLY` のままでも進める曖昧さを減らし、READY条件を明文化する。

### S28-08 Evidence Trend Index v4

- S28-01..07 の履歴点数を増やし、単発サンプル依存を解消する。
- `warn_delta` を継続監視し、劣化トレンドの早期検知を可能にする。

### S28-07 Acceptance Wall v4

- 通知実送信・baseline確定・連続運転回数の3条件を受け入れ条件に追加する。
- dry-run only の状態を PASS 扱いしない。

### S28-06 Reliability Soak v3

- 実行回数の最低ラインを設け、`INSUFFICIENT_RUNS` を解消する。
- SKIP偏重が続く場合の recovery action を明示する。

### S28-05 Policy Drift Guard v3

- baseline 初回作成を初期化フェーズへ分離し、本番評価は drift判定のみで行う。
- high-impact file の変更時に triage 連携できる形へ整える。

### S28-04 Incident Triage Pack v3

- alert の重複集約と優先順位付けを強化し、運用アクションへ直結する。
- notify/recovery の結果を triage に相互参照させる。

### S28-03 Readiness Notify v2

- dry-run 前提から実送信前提へ移行し、再送制御と送信失敗の分類を固定する。
- 入力を S28 readiness artifact 系に統一し、旧世代依存を除去する。

### S28-02 Taxonomy Feedback Loop v2

- unknown ratio 低減のため、候補抽出と収集アクションの精度を継続改善する。
- triage と接続し、unknown の放置を防ぐ。

### S28-01 Provider Canary Recovery Strategy v2

- recovery 必須状態の発生条件を絞り、skip常態化を減らす運用手当を追加する。
- strict env 未設定時の観測品質低下を evidence に即反映する。

## Planned Impacted Files

- `docs/ops/S28-01-S28-10-THREAD-V3_PLAN.md`
- `docs/ops/S28-01-S28-10-THREAD-V3_TASK.md`
- `scripts/ops/s28_provider_canary_recovery.py`
- `scripts/ops/s28_taxonomy_feedback_loop.py`
- `scripts/ops/s28_readiness_notify.py`
- `scripts/ops/s28_incident_triage_pack_v2.py`
- `scripts/ops/s28_policy_drift_guard_v2.py`
- `scripts/ops/s28_reliability_soak_v2.py`
- `scripts/ops/s28_acceptance_wall_v3.py`
- `scripts/ops/s28_evidence_trend_index_v3.py`
- `scripts/ops/s28_slo_readiness_v2.py`
- `scripts/ops/s28_closeout.py`
- `tests/test_s28_provider_canary_recovery.py`
- `tests/test_s28_taxonomy_feedback_loop.py`
- `tests/test_s28_readiness_notify.py`
- `tests/test_s28_incident_triage_pack_v2.py`
- `tests/test_s28_policy_drift_guard_v2.py`
- `tests/test_s28_reliability_soak_v2.py`
- `tests/test_s28_acceptance_wall_v3.py`
- `tests/test_s28_evidence_trend_index_v3.py`
- `tests/test_s28_slo_readiness_v2.py`
- `tests/test_s28_closeout.py`
- `docs/evidence/s28-01/*` ... `docs/evidence/s28-10/*`

## Validation Strategy

軽量:

- `make ops-now`
- `python3 -m unittest -v tests/test_s28_provider_canary_recovery.py`
- `python3 -m unittest -v tests/test_s28_readiness_notify.py`
- `python3 -m unittest -v tests/test_s28_reliability_soak_v2.py`
- `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`

中量:

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

重量（ship前）:

- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Risks and Mitigations

- リスク: provider env 未設定で SKIP が連鎖する。
- 対策: strict env の観測を定期化し、SLO に skip率を反映して早期検知する。

- リスク: webhook 実送信を有効化した際に通知失敗が増える。
- 対策: 再送制御・失敗分類・triage 連動を追加して運用吸収する。

- リスク: baseline 更新運用が曖昧で drift 判定が不安定になる。
- 対策: baseline 初期化と通常判定を分離し、PR body に更新根拠を固定する。

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  freeze READY conditions from current WARN causes
DO:
  implement S28-01..10 hardening with minimal diffs
CHECK:
  run lightweight -> medium -> heavyweight gates
SHIP:
  commit small, record command facts in PR body
```
