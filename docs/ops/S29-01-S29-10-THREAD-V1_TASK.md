# S29-01-S29-10 THREAD v1 TASK — Production-Connected Readiness Hardening

Last Updated: 2026-02-27

## Progress

- S29-01-S29-10 v1: 96% (S29-01..S29-10 実装・テスト・verify-il・ci-self green。PR body 最終反映のみ残し)

## Current Facts

- S28 closeout は `PASS` だが readiness は `WARN_ONLY`。
- S29 は soft warning / waiver を実運用接続で解消するフェーズ。
- 進捗SOTは本TASKとPR body（`STATUS.md`は非SOT）。

## Ritual 22-16-22-99

- PLAN: `docs/ops/S29-01-S29-10-THREAD-V1_PLAN.md`
- DO: チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: コマンド結果を PR body に固定

## CI Budget Rule

- 原則: `ci-self` は ship 直前の1回のみ。
- 例外: 失敗時のみ修正後1回再実行（合計2回まで）。
- Phase-1..4 ではCIを回さずローカル検証を優先する。

## Checklist

### Phase-1 Design Freeze (60m target)

- [x] 1-1. S29-10 Exit 条件と受入基準を固定
- [x] 1-2. S29-01..03 handoff 要件を実装要件へ分解
- [x] 1-3. 変更対象（script/test/evidence）を確定
- [x] 1-4. PR body 記録テンプレート（OK/WARN/ERROR/SKIP）を下書き

### Phase-2 Implementation Batch

- [x] 2-1. S29-01 canary success-rate SLO を実装
- [x] 2-2. S29-02 taxonomy pipeline integration を実装
- [x] 2-3. S29-03 notify multi-channel + retry を実装
- [x] 2-4. S29-04..10 の最小実装を連結

### Phase-3 Local Check Batch

- [x] 3-1. `make ops-now`
- [x] 3-2. `python3 -m unittest -v tests/test_s29_*.py`
- [x] 3-3. phaseごとの単体コマンドを必要分実行

### Phase-4 End-to-End Verification

- [x] 4-1. S29-01..S29-10 を順次実行
- [x] 4-2. readiness / closeout artifact を検証
- [x] 4-3. unresolved risks と handoff を確認

### Phase-5 Ship Gate

- [x] 5-1. `make verify-il`
- [x] 5-2. `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [x] 5-3. `ci-self up --ref "$(git branch --show-current)"`
- [ ] 5-4. PR body を最終更新

## Validation Commands

- `make ops-now`
- `python3 -m unittest -v tests/test_s29_*.py`
- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 各 phase で `OK:/WARN:/ERROR:/SKIP:` を最低1行残す。
- `SKIP` は理由を1行で明示する。
- 進捗/判断/コマンド結果は PR body に固定する。

## Latest Run Log (for PR body draft)

- `OK: make ops-now`（branch=`ops/S29-01-S29-10` / task=`docs/ops/S29-01-S29-10-THREAD-V1_TASK.md`）
- `OK: python3 -m unittest -v tests/test_s29_*.py`（50 tests, all green）
- `WARN: make s29-canary-recovery-success-rate-slo`（reason=`RECOVERY_REQUIRED` + success-rate soft warn）
- `WARN: make s29-taxonomy-pipeline-integration`（unknown ratio above target）
- `WARN: make s29-readiness-notify-multichannel`（dry-run）
- `WARN: make s29-incident-triage-pack-v3`（triage alert）
- `WARN: make s29-policy-drift-guard-v3`（baseline created）
- `WARN: make s29-reliability-soak-v3`（insufficient runs env gap）
- `OK: make s29-acceptance-wall-v4`
- `WARN: make s29-evidence-trend-index-v4`（phase warn aggregated）
- `WARN: make s29-slo-readiness-v3`（readiness=`WARN_ONLY`, reason=`SOFT_SLO_WARN`, waivers applied）
- `OK: make s29-closeout`（status=`PASS`, readiness=`WARN_ONLY`）
- `OK: make verify-il`
- `ERROR: ci-self up --ref \"ops/S29-01-S29-10\"`（初回: remote ref 未作成）
- `OK: git push -u origin ops/S29-01-S29-10`
- `OK: ci-self up --ref \"ops/S29-01-S29-10\"`（verify workflow green）
