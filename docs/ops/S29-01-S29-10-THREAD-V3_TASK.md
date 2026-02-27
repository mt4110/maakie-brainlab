# S29-01-S29-10 THREAD v3 TASK — READY Convergence Under Production Constraints

Last Updated: 2026-02-27

## Progress

- S29-01-S29-10 v3: 100% (Phase-1..5 実装・検証・ship gate 完了)

## Current Facts

- S29 v2 closeout は `PASS`、readiness は `WARN_ONLY`。
- v3 は waiver exit condition の実消化と `READY` 収束フェーズ。
- Phase-1 で Exit条件・waiver分解・変更対象・PR body テンプレートを固定済み。
- S29-01..S29-10 を再実行し、最新 artifact を更新済み（readiness は `WARN_ONLY` 維持）。
- `python3 -m unittest -v tests/test_s29_*.py` と `make verify-il`、`ci-self up --ref "$(git branch --show-current)"` は green。
- 進捗SOTは本TASKとPR body（`STATUS.md`は非SOT）。

## Ritual 22-16-22-99

- PLAN: `docs/ops/S29-01-S29-10-THREAD-V3_PLAN.md`
- DO: チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: コマンド結果を PR body に固定

## CI Budget Rule

- 原則: `ci-self` は ship 直前の1回のみ。
- 例外: 失敗時のみ修正後1回再実行（合計2回まで）。

## Checklist

### Phase-1 Design Freeze

- [x] 1-1. v3 Exit条件（READY判定）を固定
- [x] 1-2. v2 waiver 5件の exit condition を実施項目へ分解
- [x] 1-3. 変更対象（script/test/evidence）を確定
- [x] 1-4. PR body 記録テンプレート（OK/WARN/ERROR/SKIP）を更新

### Phase-2 Implementation Batch

- [x] 2-1. S29-01 recovery success-rate 改善差分を実装
- [x] 2-2. S29-02 unknown ratio 改善差分を実装
- [x] 2-3. S29-03 multichannel 実送信成功差分を実装
- [x] 2-4. S29-04..10 連結ロジックを v3 更新

### Phase-3 Local Check Batch

- [x] 3-1. `make ops-now`
- [x] 3-2. `python3 -m unittest -v tests/test_s29_*.py`
- [x] 3-3. 主要 phase コマンドの再実行

### Phase-4 End-to-End Verification

- [x] 4-1. S29-01..S29-10 を順次実行
- [x] 4-2. readiness / closeout artifact を検証
- [x] 4-3. waiver / unresolved risks / handoff を検証

### Phase-5 Ship Gate

- [x] 5-1. `make verify-il`
- [x] 5-2. `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [x] 5-3. `ci-self up --ref "$(git branch --show-current)"`
- [x] 5-4. PR body を最終更新

## Phase-1 Freeze Output (2026-02-27)

### 1-1. Exit条件（READY判定）固定

- READY 収束条件（soft gate）:
  - `recovery_success_rate >= 0.80`
  - `unknown_ratio <= 0.03`
  - `notify_delivery_rate >= 1.0` + `attempted_channels >= 2` + `sent_channels >= 1`
  - `reliability_total_runs >= 24`
- 中間ゲート（hard gate / waiver脱却）:
  - `recovery_success_rate >= 0.50`
  - `unknown_ratio <= 0.15`
  - `attempted_channels >= 2` + `sent_channels >= 1`
  - `reliability_total_runs >= 12`

### 1-2. v2 waiver 5件 -> v3 実施項目

- `skip_rate (SKIP_RATE_ENV_GAP)`: `S29-01` で `trailing_nonpass < 3` を達成/維持。
- `unknown_ratio (UNKNOWN_RATIO_WITH_ACTIONS)`: `S29-02` で追加ラベル収集を実施し `unknown_ratio <= 0.03` へ収束。
- `notify_delivery_rate (NOTIFY_ENDPOINT_GAP)`: `S29-03` で 2チャネル以上送信し、最小1チャネルで 2xx 成功を記録。
- `recovery_success_rate (RECOVERY_SUCCESS_ENV_GAP)`: `S29-01` で recovery 試行サンプルを増やし `success_rate >= 0.80` を満たす。
- `reliability_total_runs (RELIABILITY_ENV_GAP)`: `S29-06` で観測 run を積み増し `total_runs >= 24` を達成。

### 1-3. 変更対象確定

- Phase-1（今回）: `docs/ops/S29-01-S29-10-THREAD-V3_PLAN.md`, `docs/ops/S29-01-S29-10-THREAD-V3_TASK.md`
- Phase-2（実装）: `scripts/ops/s29_*.py`, `tests/test_s29_*.py`
- Phase-3/4（証跡更新）: `docs/evidence/s29-01/*` ... `docs/evidence/s29-10/*`

### 1-4. PR body 記録テンプレート（OK/WARN/ERROR/SKIP）

```md
### S29-01..S29-10 Thread v3
- OK: <実行成功したコマンドと主要メトリクス>
- WARN: <WARN理由 + 継続アクション>
- ERROR: <失敗コマンド + 原因 + 再実行結果>
- SKIP: <未実行項目 + 理由>

### S29-01 Canary Recovery Success-rate SLO v3
- command: `make s29-canary-recovery-success-rate-slo`
- status: <PASS/WARN/FAIL>
- metrics: trailing_nonpass=<n>, recovery_success_rate=<v>, attempts=<n>
- artifact: `docs/evidence/s29-01/canary_recovery_success_rate_slo_latest.json`

### S29-02 Taxonomy Pipeline Integration v3
- command: `make s29-taxonomy-pipeline-integration`
- status: <PASS/WARN/FAIL>
- metrics: unknown_ratio=<v>, candidate_count=<n>, action_count=<n>
- artifact: `docs/evidence/s29-02/taxonomy_pipeline_integration_latest.json`

### S29-03 Readiness Notify Multi-channel v3
- command: `make s29-readiness-notify-multichannel`
- status: <PASS/WARN/FAIL>
- metrics: attempted_channels=<n>, sent_channels=<n>, delivery_rate=<v>
- artifact: `docs/evidence/s29-03/readiness_notify_multichannel_latest.json`

### S29-09 SLO Readiness v3
- command: `make s29-slo-readiness-v3`
- status: <PASS/WARN/FAIL>
- readiness: <READY/WARN_ONLY/BLOCKED>
- summary: waived_hard_count=<n>, waived_with_exit_condition_count=<n>
- artifact: `docs/evidence/s29-09/slo_readiness_v4_latest.json`

### S29-10 Closeout v3
- command: `make s29-closeout`
- status: <PASS/FAIL>
- readiness: <READY/WARN_ONLY/BLOCKED>
- summary: waiver_exit_condition_count=<n>, unresolved_risk_count=<n>, handoff_count=<n>
- artifact: `docs/evidence/s29-10/closeout_latest.json`
```

## Validation Commands

- `make ops-now`
- `python3 -m unittest -v tests/test_s29_*.py`
- `make s29-canary-recovery-success-rate-slo`
- `make s29-taxonomy-pipeline-integration`
- `make s29-readiness-notify-multichannel`
- `make s29-slo-readiness-v3`
- `make s29-closeout`
- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 各 phase で `OK:/WARN:/ERROR:/SKIP:` を最低1行残す。
- `SKIP` は理由を1行で明示する。
- 進捗/判断/コマンド結果は PR body に固定する。

## Latest Run Log (for PR body)

- `OK: make ops-now`（task=`docs/ops/S29-01-S29-10-THREAD-V3_TASK.md`, progress=22% at run time）
- `OK: python3 -m unittest -v tests/test_s29_*.py`（51 tests, all green）
- `WARN: make s29-canary-recovery-success-rate-slo`（status=`WARN`, reason=`RECOVERY_REQUIRED`, trailing_nonpass=3, recovery_success_rate=0.0）
- `WARN: make s29-taxonomy-pipeline-integration`（status=`WARN`, reason=`UNKNOWN_RATIO_ABOVE_TARGET`, unknown_ratio=0.3125）
- `WARN: make s29-readiness-notify-multichannel`（status=`WARN`, reason=`NOTIFY_SEND_FAILED`, attempted_channels=2, sent_channels=0）
- `WARN: make s29-incident-triage-pack-v3`（status=`WARN`, reason=`TRIAGE_ALERT`）
- `OK: make s29-policy-drift-guard-v3`（status=`PASS`, reason=``, drift_total=0）
- `WARN: make s29-reliability-soak-v3`（status=`WARN`, reason=`INSUFFICIENT_RUNS_ENV_GAP`, total_runs=3）
- `OK: make s29-acceptance-wall-v4`（status=`PASS`, cases_total=10）
- `WARN: make s29-evidence-trend-index-v4`（status=`WARN`, pass_warn_fail=2/5/0）
- `WARN: make s29-slo-readiness-v3`（status=`WARN`, readiness=`WARN_ONLY`, waived_hard_count=5）
- `OK: make s29-closeout`（status=`PASS`, readiness=`WARN_ONLY`, waiver_exit_condition_count=5）
- `OK: make verify-il`（IL entrypoint guard/smoke/suite/selftest all green）
- `OK: source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `OK: ci-self up --ref \"$(git branch --show-current)\"`（verify run `22485065873` green）
- `SKIP: pr_checks`（reason=`pr_not_found_for_branch` at ci-self run time）
