# S28-01-S28-10 THREAD v2 TASK — WARN_ONLY to READY Hardening

Last Updated: 2026-02-27

## Progress

- S28-01-S28-10 v2: 88% (S28-01..S28-10 実装・テスト・中量実行まで完了。READY化とship前重検証が残り)

## Latest Facts (2026-02-27)

- `S28-09`: `BLOCKED` (`HARD_SLO_VIOLATION`, `hard_block_count=4`)
- hard violations: `skip_rate`, `unknown_ratio`, `notify_delivery_rate`, `reliability_total_runs`
- `S28-10`: `FAIL`（readiness=`BLOCKED`）で closeout artifact は更新済み

## Ritual 22-16-22-99

- PLAN: `docs/ops/S28-01-S28-10-THREAD-V2_PLAN.md`
- DO: 下記チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: 小分けコミット + PR body に結果固定

## Current-Point Rule (SOT)

- 現在地は `branch + TASK progress + checklist未完了先頭` の3点で定義する。
- 進捗 SOT は本 TASK と PR body（`STATUS.md` には依存しない）。
- 毎作業開始時に `make ops-now` を実行し、同じ形式で確認する。

## Exit Metrics (v2)

- `readiness=READY`
- `skip_rate <= 0.20`
- `notify_delivery_rate >= 0.95`
- `unknown_ratio <= 0.05`
- `reliability total_runs >= 24`

## Checklist

### S28-00 Kickoff

- [x] S28 v2 PLAN/TASK を新規作成
- [x] v1 evidence の WARN要因を抽出し、v2 DoD を固定
- [ ] PR body に v2 の exit metrics ブロックを追加

### S28-01 Provider Canary Recovery Strategy v2

- [x] skip常態化の原因分類を追加（env/config/runtime）
- [x] recovery action の自動提案精度を改善
- [x] evidence（JSON/MD）を `docs/evidence/s28-01/` に保存
- [x] unit tests を追加/更新（SKIP低減判定）

### S28-02 Taxonomy Feedback Loop v2

- [x] unknown候補抽出ルールを調整
- [x] triage向け action 連携を追加
- [x] evidence（JSON/MD）を `docs/evidence/s28-02/` に保存
- [x] unit tests を追加/更新（unknown_ratio制御）

### S28-03 Readiness Notify v2

- [x] S28 readiness入力へ統一（旧世代入力参照を除去）
- [x] 実送信+再送制御を実装（dry-run依存を解消）
- [x] evidence（JSON/MD）を `docs/evidence/s28-03/` に保存
- [x] unit tests を追加/更新（delivery_rate算出）

### S28-04 Incident Triage Pack v3

- [x] alert 重複集約ロジックを追加
- [x] notify/recovery結果の相互参照を追加
- [x] evidence（JSON/MD）を `docs/evidence/s28-04/` に保存
- [x] unit tests を追加/更新（priority_actions妥当性）

### S28-05 Policy Drift Guard v3

- [x] baseline初期化フローと通常判定フローを分離
- [x] high-impact変更時の出力を明確化
- [x] evidence（JSON/MD）を `docs/evidence/s28-05/` に保存
- [x] unit tests を追加/更新（baseline/scan分岐）

### S28-06 Reliability Soak v3

- [x] 最低実行回数 gate（`total_runs >= 24`）を導入
- [x] SKIP偏重時の recovery recommendation を強化
- [x] evidence（JSON/MD）を `docs/evidence/s28-06/` に保存
- [x] unit tests を追加/更新（run数/閾値判定）

### S28-07 Acceptance Wall v4

- [x] 通知実送信・baseline確定・連続運転の受け入れケースを追加
- [x] severity判定を v2 DoD に追従させる
- [x] evidence（JSON/MD）を `docs/evidence/s28-07/` に保存
- [x] unit tests を追加/更新（新ケース追加）

### S28-08 Evidence Trend Index v4

- [x] 履歴点数を増やし trend判定を強化
- [x] warn_delta 監視ルールを追加
- [x] evidence（JSON/MD）を `docs/evidence/s28-08/` に保存
- [x] unit tests を追加/更新（history増分判定）

### S28-09 SLO Readiness v3

- [x] READY条件を v2 Exit Metrics へ更新
- [x] hard/soft violation 判定を再調整
- [x] evidence（JSON/MD）を `docs/evidence/s28-09/` に保存
- [x] unit tests を追加/更新（gate一貫性）

### S28-10 Closeout v2

- [x] closeout note を v2反映
- [x] Before/After + unresolved risk + S29 handoff を更新
- [x] evidence（JSON/MD）を `docs/evidence/s28-10/` に保存
- [x] unit tests を追加/更新

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
- [x] `make s28-slo-readiness-v2` (実行済み / `HARD_SLO_VIOLATION`)
- [x] `make s28-closeout` (実行済み / readiness=`BLOCKED`)

重量（ship前）:

- [ ] `make verify-il`
- [ ] `source /path/to/your/nix/profile.d/nix-daemon.sh`
- [ ] `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は PR body に固定する。
- 各 phase で最低1行の `OK:/WARN:/ERROR:/SKIP:` を残す。
- `SKIP` は理由を1行で明示する。
