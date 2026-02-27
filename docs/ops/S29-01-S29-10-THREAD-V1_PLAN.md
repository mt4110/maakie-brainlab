# S29-01-S29-10 THREAD v1 PLAN — Production-Connected Readiness Hardening

Last Updated: 2026-02-27

## Goal

- S28 closeout で `WARN_ONLY` として残した soft warning / waiver を、実運用接続前提の判定へ引き上げる。
- S29-01..S29-10 を一気通貫で設計し、`READY` 判定までの不足条件を段階的に解消する。
- CI消費を抑えるため、実装中のCI連打を避け、ship直前の最終ゲートへ集約する。

## Current Point (2026-02-27)

- Branch: `ops/S28-01-S28-10`
- S28 closeout summary:
  - `status=PASS`
  - `readiness=WARN_ONLY`
  - `waived_hard_count=4`
  - `unresolved_risk_count=12`
- S28 -> S29 handoff:
  1. `S29-01`: canary 自動復旧の実行成功率SLOを導入
  2. `S29-02`: taxonomy feedback loop をデータ生成パイプラインへ統合
  3. `S29-03`: readiness 通知のマルチチャネル配信と再送制御を導入

## Non-negotiables

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、blocking gate を増やさない。
- `docs/ops/STATUS.md` を進捗SOTに使わない（TASK + PR bodyに固定）。
- PR作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行し、green確認後に進める。
- 禁止ブランチ `codex/feat*` は使わない。

## Cadence Policy (Slow + One-pass)

- Phase-1 設計固定を厚めに確保（目安60分）。
- Phase-2 で実装を1バッチに集約し、途中CIは実行しない。
- `ci-self` はship直前1回を原則とし、失敗時のみ再試行1回まで。

## Completion Definition (S29-10 Exit)

- `S29-09` で readiness が `READY` または根拠付き `WARN_ONLY` に収束し、判定理由が artifact に固定される。
- `S29-10` closeout が unresolved risk の Before/After と S30 handoff を出力する。
- S29関連の unit tests と一気通貫実行が green。
- `verify-il` と `ci-self` が green。

## Backward Design (S29-10 -> S29-01)

### S29-10 Closeout + S30 Handoff
- S29成果、残リスク、次スレ移管条件を1 artifactへ固定する。

### S29-09 SLO Readiness v3
- 実運用接続指標（delivery / recovery success / taxonomy throughput）を含むGo/No-Goを出力する。

### S29-08 Evidence Trend Index v4
- S29-01..07 の履歴を時系列 index 化し、欠損/劣化を即判定可能にする。

### S29-07 Acceptance Wall v4
- 実運用接続を含む受入条件を severity 付きで評価する。

### S29-06 Reliability Soak v3
- recovery実行成功率と連続劣化を統合し、運用耐性を可視化する。

### S29-05 Policy Drift Guard v3
- S29 contract 群の drift を継続検知する。

### S29-04 Incident Triage Pack v3
- canary/taxonomy/notify の実運用シグナルを triage packet に統合する。

### S29-03 Readiness Notify Multi-channel
- 通知を複数チャネルへ配信し、再送制御と失敗可観測性を実装する。

### S29-02 Taxonomy Feedback Pipeline Integration
- unknown候補を収集して終わらせず、データ生成パイプラインに接続する。

### S29-01 Canary Recovery Success-rate SLO
- 自動復旧の試行数/成功数/成功率を契約化し、SLO評価に接続する。

## Planned Impacted Files

- `docs/ops/S29-01-S29-10-THREAD-V1_PLAN.md`
- `docs/ops/S29-01-S29-10-THREAD-V1_TASK.md`
- `docs/ops/ROADMAP.md`
- `scripts/ops/s29_*.py`（phaseごとに追加）
- `tests/test_s29_*.py`（phaseごとに追加）
- `docs/evidence/s29-01/*` ... `docs/evidence/s29-10/*`

## Validation Strategy

軽量:
- `make ops-now`
- `python3 -m unittest -v tests/test_s29_*.py`

中量:
- `make s29-canary-recovery-success-rate-slo` ... `make s29-closeout`（S29用ターゲット群）

重量（ship前）:
- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  freeze S29 acceptance criteria, scope, and CI budget
DO:
  implement S29 phases in one cohesive batch when feasible
CHECK:
  run local tests and one end-to-end run before CI
SHIP:
  run verify-il and ci-self once, then fix PR body evidence
```
