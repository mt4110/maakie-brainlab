# S29-01-S29-10 THREAD v2 PLAN — WARN_ONLY Waiver Burn-down

Last Updated: 2026-02-27

## Goal

- S29 v1 の `readiness=WARN_ONLY` を前提に、waiver 依存の判定を削減して `READY` 到達条件を明確化する。
- 実運用接続（通知実送信・recovery 成功率・taxonomy pipeline 投入）を再実行し、S29-09 判定を収束させる。
- S29-10 closeout を v2 更新し、S30 handoff を運用可能な粒度で固定する。

## Current Point (2026-02-27)

- Branch: `ops/S29-01-S29-10`
- S29 v1 summary:
  - `status=PASS` (S29-10 closeout)
  - `readiness=WARN_ONLY` (S29-09)
  - `waived_hard_count=5`
  - `unresolved_risk_count=14`
- Dominant WARN factors:
  1. notify multi-channel が dry-run（実送信未実施）
  2. reliability soak の runs 不足（env gap 起因）
  3. taxonomy unknown ratio 高止まり
  4. recovery success-rate が soft warn

## Non-negotiables

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、blocking gate を増やさない。
- `docs/ops/STATUS.md` を進捗SOTに使わない（TASK + PR bodyに固定）。
- PR作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行し、green確認後に進める。
- 禁止ブランチ `codex/feat*` は使わない。

## Completion Definition (S29-10 Exit v2)

- `S29-09` で `readiness=READY` を第一目標とし、未達時は `WARN_ONLY` の根拠（waiver code + exit condition）を artifact へ固定。
- `S29-03` は2チャネル以上で送信試行が記録される（`attempted_channels >= 2`）。
- `S29-06` は `target_runs` 到達、または env gap の運用制約を明文化。
- `S29-10` closeout v2 に Before/After・未解決リスク・S30 handoff を更新。
- `tests/test_s29_*.py`, `make verify-il`, `ci-self` が green。

## Backward Design (S29-10 -> S29-01)

### S29-10 Closeout v2
- v1 との差分（waiver減少、送信実績、soak継続）を固定。

### S29-09 SLO Readiness v4
- recovery success-rate / multichannel delivery / taxonomy pipeline throughput の閾値を再評価。

### S29-08 Evidence Trend Index v5
- S29-01..07 の trend 劣化を即時検知できる履歴条件を追加。

### S29-07 Acceptance Wall v5
- multi-channel 実送信・pipeline 出力・recovery SLO の受入ケースを追加。

### S29-06 Reliability Soak v4
- runs不足 WARN を減らすため継続観測を反映。

### S29-05 Policy Drift Guard v4
- S29 contract 群の変更監視を v4 baseline へ移行。

### S29-04 Incident Triage Pack v4
- v2 実運用指標（送信結果・pipeline record・recovery SLO）を優先アクションへ統合。

### S29-03 Readiness Notify Multi-channel v2
- 実送信実績を作り、再送失敗の分類を固定。

### S29-02 Taxonomy Pipeline Integration v2
- candidates を pipeline へ投入し、owner/action を artifact 化。

### S29-01 Canary Recovery Success-rate SLO v2
- sample 不足・低成功率の改善ループを回す。

## Planned Impacted Files

- `docs/ops/S29-01-S29-10-THREAD-V2_PLAN.md`
- `docs/ops/S29-01-S29-10-THREAD-V2_TASK.md`
- `docs/ops/ROADMAP.md`
- `scripts/ops/s29_*.py`（v2差分）
- `tests/test_s29_*.py`（v2差分）
- `docs/evidence/s29-01/*` ... `docs/evidence/s29-10/*`

## Validation Strategy

軽量:
- `make ops-now`
- `python3 -m unittest -v tests/test_s29_*.py`

中量:
- `make s29-canary-recovery-success-rate-slo`
- `make s29-taxonomy-pipeline-integration`
- `make s29-readiness-notify-multichannel`
- `make s29-slo-readiness-v3`
- `make s29-closeout`

重量（ship前）:
- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`
