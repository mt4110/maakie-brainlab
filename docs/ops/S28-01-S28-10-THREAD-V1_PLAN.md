# S28-01-S28-10 THREAD v1 PLAN — Recovery-Centric Ops Automation

Last Updated: 2026-02-27

## Goal

- S27 handoff の3項目（自動復旧 / taxonomy unknown 削減 / readiness 通知）を起点に、運用判定を1スレッドで完結させる。
- S28-10 Exit 時点で、`recovery -> feedback -> notify -> triage -> drift -> soak -> acceptance -> trend -> slo -> closeout` が再現可能になる。

## Current Point (as of 2026-02-27)

- ブランチ: `ops/S28-01-S28-10`
- `make ops-now` は S27 TASK を参照しており、S28 専用 TASK/PLAN 未作成。
- S27 closeout handoff で確定済み着手項目は `S28-01..S28-03`。

## Constraints (Non-negotiable)

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、blocking gate を増やさない。
- `docs/ops/STATUS.md` を進捗 SOT にしない。進捗は TASK と PR body に固定する。
- ship 前に `ci-self up --ref "$(git branch --show-current)"` を実行し、全 green を確認してから PR 更新する。
- ブランチ禁止パターン `codex/feat*` を使わない。

## Completion Definition (S28-10 Exit)

- canary 自動復旧戦略が artifact 化され、連続 non-pass の判定が固定される。
- taxonomy feedback loop で unknown case の収集アクションが自動生成される。
- readiness notify が message payload を固定し、送信失敗も可視化される。
- triage/drift/soak/acceptance/index/slo が S28 artifact 群で連結される。
- closeout artifact に Before/After・unresolved risk・S29 handoff が固定される。

## Backward Phase Design (S28-10 -> S28-01)

### S28-10 Closeout + S29 Handoff
- S28成果を1 artifactに集約し、S29開始条件を固定する。

### S28-09 SLO Readiness v2
- S28-01..08 を統合し、READY / WARN_ONLY / BLOCKED を出力する。

### S28-08 Evidence Trend Index v3
- S28-01..07 の履歴 index を生成し、欠損/劣化を即判定できるようにする。

### S28-07 Acceptance Wall v3
- S28 artifact 群の受け入れ条件を severity付きで評価する。

### S28-06 Reliability Soak v2
- history の non-pass streak と recovery signal を合成し、運用劣化を可視化する。

### S28-05 Policy Drift Guard v2
- S28 contract file 群の drift を継続検知する。

### S28-04 Incident Triage Pack v2
- recovery/taxonomy/notify を含む triage packet を生成する。

### S28-03 Readiness Notify
- readiness 判定を運用チャンネル向けメッセージに変換し、配信導線を作る。

### S28-02 Taxonomy Feedback Loop
- unknown case 候補を抽出し、データ収集アクションを自動化する。

### S28-01 Provider Canary Recovery Strategy
- canary history から連続 non-pass を検知し、自動復旧戦略を固定する。

## Planned Impacted Files

- `docs/ops/S28-01-S28-10-THREAD-V1_PLAN.md`
- `docs/ops/S28-01-S28-10-THREAD-V1_TASK.md`
- `docs/ops/S28-01_PROVIDER_CANARY_RECOVERY.toml`
- `docs/ops/S28-02_TAXONOMY_FEEDBACK_LOOP.toml`
- `docs/ops/S28-07_ACCEPTANCE_CASES_V3.json`
- `docs/ops/S28-10_CLOSEOUT.md`
- `scripts/ops/s28_*.py` (10 files)
- `tests/test_s28_*.py` (10 files)
- `Makefile`
- `docs/ops/ROADMAP.md`
- `docs/evidence/s28-01/*` ... `docs/evidence/s28-10/*`

## Validation Strategy

軽量:
- `make ops-now`
- `python3 -m unittest -v tests/test_s28_provider_canary_recovery.py`
- `python3 -m unittest -v tests/test_s28_taxonomy_feedback_loop.py`
- `python3 -m unittest -v tests/test_s28_readiness_notify.py`
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
