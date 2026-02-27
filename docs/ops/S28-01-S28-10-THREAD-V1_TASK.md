# S28-01-S28-10 THREAD v1 TASK — Recovery-Centric Ops Automation

Last Updated: 2026-02-27

## Progress

- S28-01-S28-10: 96% (S28-01..S28-10 implementation/evidence/test complete, ship前ci-self gateのみ残し)

## Ritual 22-16-22-99

- PLAN: `docs/ops/S28-01-S28-10-THREAD-V1_PLAN.md`
- DO: 下記チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: 小分けコミット + PR body に結果固定

## Current-Point Rule (SOT)

- 現在地は `branch + TASK progress + checklist未完了先頭` の3点で定義する。
- 進捗 SOT は本 TASK と PR body（`STATUS.md` には依存しない）。
- 毎作業開始時に `make ops-now` を実行し、同じ形式で確認する。

## Checklist

### S28-00 Kickoff

- [x] S28 thread の PLAN/TASK を新規作成
- [x] S28-10 Exit と backward design（S28-10 -> S28-01）を固定
- [x] S27 handoff（S28-01..03）との整合を明記

### S28-01 Provider Canary Recovery Strategy

- [x] recovery policy を TOML で定義
- [x] `scripts/ops/s28_provider_canary_recovery.py` を追加
- [x] evidence（JSON/MD）を `docs/evidence/s28-01/` に保存
- [x] unit tests を追加（streak判定/復旧判定）

### S28-02 Taxonomy Feedback Loop

- [x] feedback loop policy を TOML で定義
- [x] `scripts/ops/s28_taxonomy_feedback_loop.py` を追加
- [x] evidence（JSON/MD）を `docs/evidence/s28-02/` に保存
- [x] unit tests を追加（候補抽出/アクション生成）

### S28-03 Readiness Notify

- [x] `scripts/ops/s28_readiness_notify.py` を追加
- [x] webhook 送信/未設定時の非停止挙動を実装
- [x] evidence（JSON/MD）を `docs/evidence/s28-03/` に保存
- [x] unit tests を追加（message生成/送信判定）

### S28-04 Incident Triage Pack v2

- [x] `scripts/ops/s28_incident_triage_pack_v2.py` を追加
- [x] recovery/taxonomy/notify の集約を実装
- [x] evidence（JSON/MD）を `docs/evidence/s28-04/` に保存
- [x] unit tests を追加（reason集計/優先アクション）

### S28-05 Policy Drift Guard v2

- [x] `scripts/ops/s28_policy_drift_guard_v2.py` を追加
- [x] S28 watch files の hash 比較を実装
- [x] evidence（JSON/MD）を `docs/evidence/s28-05/` に保存
- [x] unit tests を追加（scan/diff）

### S28-06 Reliability Soak v2

- [x] `scripts/ops/s28_reliability_soak_v2.py` を追加
- [x] non-pass streak と recovery signal 集計を実装
- [x] evidence（JSON/MD）を `docs/evidence/s28-06/` に保存
- [x] unit tests を追加（連続判定/閾値判定）

### S28-07 Acceptance Wall v3

- [x] acceptance cases v3 を追加
- [x] `scripts/ops/s28_acceptance_wall_v3.py` を追加
- [x] evidence（JSON/MD）を `docs/evidence/s28-07/` に保存
- [x] unit tests を追加（ケース検証/severity判定）

### S28-08 Evidence Trend Index v3

- [x] `scripts/ops/s28_evidence_trend_index_v3.py` を追加
- [x] S28-01..07 の履歴 index を生成
- [x] evidence（JSON/MD）を `docs/evidence/s28-08/` に保存
- [x] unit tests を追加（index整合/summary判定）

### S28-09 SLO-based Go/No-Go v2

- [x] `scripts/ops/s28_slo_readiness_v2.py` を追加
- [x] notify delivery を含む SLO 合成を実装
- [x] evidence（JSON/MD）を `docs/evidence/s28-09/` に保存
- [x] unit tests を追加（SLO評価/ゲート判定）

### S28-10 Closeout

- [x] closeout note を `docs/ops/S28-10_CLOSEOUT.md` に追加
- [x] `scripts/ops/s28_closeout.py` を追加
- [x] Before/After + unresolved risk + S29 handoff を artifact 化
- [x] unit tests を追加

## Validation Commands

軽量（毎PR）:

- [x] `make ops-now`
- [x] `python3 -m unittest -v tests/test_s28_provider_canary_recovery.py`
- [x] `python3 -m unittest -v tests/test_s28_taxonomy_feedback_loop.py`
- [x] `python3 -m unittest -v tests/test_s28_readiness_notify.py`
- [x] `python3 -m unittest -v tests/test_s28_incident_triage_pack_v2.py`
- [x] `python3 -m unittest -v tests/test_s28_policy_drift_guard_v2.py`
- [x] `python3 -m unittest -v tests/test_s28_reliability_soak_v2.py`
- [x] `python3 -m unittest -v tests/test_s28_acceptance_wall_v3.py`
- [x] `python3 -m unittest -v tests/test_s28_evidence_trend_index_v3.py`
- [x] `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`
- [x] `python3 -m unittest -v tests/test_s28_closeout.py`

中量（必要時）:

- [x] `make s28-provider-canary-recovery`
- [x] `make s28-taxonomy-feedback-loop`
- [x] `make s28-readiness-notify`
- [x] `make s28-incident-triage-pack-v2`
- [x] `make s28-policy-drift-guard-v2`
- [x] `make s28-reliability-soak-v2`
- [x] `make s28-acceptance-wall-v3`
- [x] `make s28-evidence-trend-index-v3`
- [x] `make s28-slo-readiness-v2`
- [x] `make s28-closeout`

重量（ship前）:

- [x] `make verify-il`
- [ ] `source /path/to/your/nix/profile.d/nix-daemon.sh`
- [ ] `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は PR body に固定する。
- 各 phase で最低1行の `OK:/WARN:/ERROR:/SKIP:` を残す。
- `SKIP` は理由を1行で明示する。
