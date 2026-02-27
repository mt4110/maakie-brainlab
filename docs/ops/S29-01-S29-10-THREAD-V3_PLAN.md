# S29-01-S29-10 THREAD v3 PLAN — READY Convergence Under Production Constraints

Last Updated: 2026-02-27

## Goal

- S29 v2 の `readiness=WARN_ONLY` から、waiver exit condition を実運用証跡で消化して `READY` へ収束させる。
- `attempted_channels >= 2` を維持しつつ、実送信成功（2xx）を伴う通知経路を最小1チャネルで確立する。
- S29-10 closeout を v3 更新し、S30 handoff を「残課題の実施順」まで固定する。

## Current Point (2026-02-27)

- Branch: `ops/S29-01-S29-10`
- S29 v2 summary:
  - `status=PASS` (S29-10 closeout)
  - `readiness=WARN_ONLY` (S29-09)
  - `waived_hard_count=5`
  - `waived_with_exit_condition_count=5`
- Dominant WARN factors:
  1. notify は `attempted_channels=2` だが `delivery_rate=0.0`
  2. reliability total runs 不足（`total_runs=3`）
  3. taxonomy unknown ratio 高止まり（`0.3125`）
  4. recovery success-rate 低位（`0.0`）

## Non-negotiables

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、blocking gate を増やさない。
- `docs/ops/STATUS.md` を進捗SOTに使わない（TASK + PR bodyに固定）。
- PR作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行し、green確認後に進める。
- 禁止ブランチ `codex/feat*` は使わない。

## Completion Definition (S29-10 Exit v3)

- `S29-09` で `readiness=READY` を第一目標とする。
- `S29-03` で `attempted_channels >= 2` かつ `sent_channels >= 1` を達成する。
- `S29-06` で `total_runs >= 12`（hard min 到達）を達成する。
- `S29-02` で `unknown_ratio <= 0.15`（hard threshold 以下）を達成する。
- `S29-01` で `recovery_success_rate >= 0.50`（hard threshold 以上）を達成する。
- `tests/test_s29_*.py`, `make verify-il`, `ci-self` が green。

## Backward Design (S29-10 -> S29-01)

### S29-10 Closeout v3
- v2 との差分（waiver解消数、送信成功、soak runs増加）を fixed facts として記録する。

### S29-09 SLO Readiness v5
- v4 waiver を減算し、hard violation の残数を最小化する。

### S29-08 Evidence Trend Index v6
- 各 phase の regression 検知を継続し、劣化フェーズの即時特定を維持する。

### S29-07 Acceptance Wall v6
- `attempted_channels` と `sent_channels` の両方を受入条件として維持する。

### S29-06 Reliability Soak v5
- `target_runs` 到達までの不足分を定量管理し、env gap理由を縮小する。

### S29-05 Policy Drift Guard v5
- v4 baseline を起点に drift のみを評価し、運用雑音を減らす。

### S29-04 Incident Triage Pack v5
- exit conditions の実施状況をアクションステータスとして追跡する。

### S29-03 Readiness Notify Multi-channel v3
- 実送信成功チャネルの確立と失敗理由の再分類を実施する。

### S29-02 Taxonomy Pipeline Integration v3
- owner/action ベースで unknown backlog を優先消化する。

### S29-01 Canary Recovery Success-rate SLO v3
- recovery attempts のサンプル不足を解消し、success-rate を hard threshold 以上へ引き上げる。

## Planned Impacted Files

- `docs/ops/S29-01-S29-10-THREAD-V3_PLAN.md`
- `docs/ops/S29-01-S29-10-THREAD-V3_TASK.md`
- `docs/ops/ROADMAP.md`
- `scripts/ops/s29_*.py`（v3差分）
- `tests/test_s29_*.py`（v3差分）
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
