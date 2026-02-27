# S27-01-S27-10 THREAD v1 TASK — Continuous Canary Ops and Readiness Automation

Last Updated: 2026-02-27

## Progress

- S27-01-S27-10: 98% (S27-01..S27-10 implementation/evidence complete, ship前ci-self gateのみ残し)

## Ritual 22-16-22-99

- PLAN: `docs/ops/S27-01-S27-10-THREAD-V1_PLAN.md`
- DO: 下記チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: 小分けコミット + PR body に結果固定

## Current-Point Rule (SOT)

- 現在地は `branch + TASK progress + checklist未完了先頭` の3点で定義する。
- 進捗 SOT は本 TASK と PR body（`STATUS.md` には依存しない）。
- 毎作業開始時に `make ops-now` を実行し、同じ形式で確認する。

## Checklist

### S27-00 Kickoff

- [x] S27 thread の PLAN/TASK を新規作成
- [x] S27-10 Exit と backward design（S27-10 -> S27-01）を固定
- [x] S26 handoff（S27-01..03）との整合を明記

### S27-01 Provider Canary Operations

- [x] canary policy v2（`skip_rate_warn_threshold`, `window_size`）を TOML で定義
- [x] `scripts/ops/s27_provider_canary_ops.py` を追加
- [x] run 履歴ベースの SKIP率 trend 集計を実装
- [x] evidence（JSON/MD）を `docs/evidence/s27-01/` に保存
- [x] unit tests を追加（閾値判定/履歴窓/未設定env）

### S27-02 Medium Eval Wall v2

- [x] medium dataset を運用ケース入り v2 へ拡張
- [x] taxonomy v2（provider/network/schema/timeout/unknown）を固定
- [x] `scripts/ops/s27_medium_eval_wall_v2.py` を追加
- [x] evidence（JSON/MD）を `docs/evidence/s27-02/` に保存
- [x] unit tests を追加（dataset/schema/分類集計）

### S27-03 Release Readiness to CI Schedule

- [x] readiness runner の schedule 実行導線を追加
- [x] `.github/workflows/run_always_1h.yml` との連携を実装
- [x] `scripts/ops/s27_release_readiness_schedule.py` を追加
- [x] evidence（JSON/MD）を `docs/evidence/s27-03/` に保存
- [x] unit tests を追加（schedule入力/manual互換）

### S27-04 Incident Triage Pack

- [x] `scripts/ops/s27_incident_triage_pack.py` を追加
- [x] top reason_code / failed runs / rollback command を集約
- [x] evidence（JSON/MD）を `docs/evidence/s27-04/` に保存
- [x] unit tests を追加（集約欠損/表示整合）

### S27-05 Policy Drift Guard

- [x] `scripts/ops/s27_policy_drift_guard.py` を追加
- [x] TOML/JSON schema hash 比較を実装
- [x] drift レポート（WARN/ERROR分類）を出力
- [x] evidence（JSON/MD）を `docs/evidence/s27-05/` に保存
- [x] unit tests を追加（hash差分/分類ロジック）

### S27-06 Reliability Soak

- [x] `scripts/ops/s27_reliability_soak.py` を追加
- [x] 長時間 run の連続失敗/時間帯偏り集計を実装
- [x] soak しきい値と判定仕様を docs に固定
- [x] evidence（JSON/MD）を `docs/evidence/s27-06/` に保存
- [x] unit tests を追加（時系列集計/閾値判定）

### S27-07 Acceptance Wall v2

- [x] acceptance cases v2（severity/fallback）を追加
- [x] `scripts/ops/s27_acceptance_wall_v2.py` を追加
- [x] severity 別の pass/fail 集計を実装
- [x] evidence（JSON/MD）を `docs/evidence/s27-07/` に保存
- [x] unit tests を追加（case schema/集計）

### S27-08 Evidence Trend Index v2

- [x] `scripts/ops/s27_evidence_trend_index.py` を追加
- [x] S27-01..07 の履歴 index を生成
- [x] missing/failed/warn 推移を markdown table 化
- [x] evidence（JSON/MD）を `docs/evidence/s27-08/` に保存
- [x] unit tests を追加（index整合/欠損検知）

### S27-09 SLO-based Go/No-Go

- [x] `scripts/ops/s27_slo_readiness.py` を追加
- [x] `READY/BLOCKED/WARN_ONLY` 判定を実装
- [x] HARD_BLOCK と SOFT_WARN の分類根拠を出力
- [x] evidence（JSON/MD）を `docs/evidence/s27-09/` に保存
- [x] unit tests を追加（境界値/判定根拠）

### S27-10 Closeout

- [x] closeout note を `docs/ops/S27-10_CLOSEOUT.md` に追加
- [x] `scripts/ops/s27_closeout.py` を追加
- [x] Before/After + unresolved risk + S28 handoff を artifact 化
- [x] evidence（JSON/MD）を `docs/evidence/s27-10/` に保存
- [x] unit tests を追加

## Validation Commands

軽量（毎PR）:

- [x] `make ops-now`
- [x] `python3 -m unittest -v tests/test_s27_provider_canary_ops.py`
- [x] `python3 -m unittest -v tests/test_s27_medium_eval_wall_v2.py`
- [x] `python3 -m unittest -v tests/test_s27_release_readiness_schedule.py`
- [x] `python3 -m unittest -v tests/test_s27_policy_drift_guard.py`
- [x] `python3 -m unittest -v tests/test_s27_evidence_trend_index.py`
- [x] `python3 -m unittest -v tests/test_s27_slo_readiness.py`

中量（必要時）:

- [x] `make s27-provider-canary-ops`
- [x] `make s27-medium-eval-wall-v2`
- [x] `make s27-release-readiness-schedule`
- [x] `make s27-incident-triage-pack`
- [x] `make s27-policy-drift-guard`
- [x] `make s27-reliability-soak`
- [x] `make s27-acceptance-wall-v2`
- [x] `make s27-evidence-trend-index`
- [x] `make s27-slo-readiness`
- [x] `make s27-closeout`

重量（ship前）:

- [x] `make verify-il`
- [x] `source /path/to/your/nix/profile.d/nix-daemon.sh`
- [x] `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は PR body に固定する。
- 各 phase で最低1行の `OK:/WARN:/ERROR:/SKIP:` を残す。
- `SKIP` は理由を1行で明示する。

## Commit Strategy

- 1 phase = 1 commit を基本とする（review と rollback を容易にする）。
- commit message 例:
  - `ops(s27-01): add provider canary ops skip-rate monitoring`
  - `ops(s27-03): schedule release readiness in ci`
  - `ops(s27-09): add slo-based readiness decision`
