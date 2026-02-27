# S29-01-S29-10 THREAD v1 TASK — Production-Connected Readiness Hardening

Last Updated: 2026-02-27

## Progress

- S29-01-S29-10 v1: 0% (kickoff pending)

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

- [ ] 1-1. S29-10 Exit 条件と受入基準を固定
- [ ] 1-2. S29-01..03 handoff 要件を実装要件へ分解
- [ ] 1-3. 変更対象（script/test/evidence）を確定
- [ ] 1-4. PR body 記録テンプレート（OK/WARN/ERROR/SKIP）を下書き

### Phase-2 Implementation Batch

- [ ] 2-1. S29-01 canary success-rate SLO を実装
- [ ] 2-2. S29-02 taxonomy pipeline integration を実装
- [ ] 2-3. S29-03 notify multi-channel + retry を実装
- [ ] 2-4. S29-04..10 の最小実装を連結

### Phase-3 Local Check Batch

- [ ] 3-1. `make ops-now`
- [ ] 3-2. `python3 -m unittest -v tests/test_s29_*.py`
- [ ] 3-3. phaseごとの単体コマンドを必要分実行

### Phase-4 End-to-End Verification

- [ ] 4-1. S29-01..S29-10 を順次実行
- [ ] 4-2. readiness / closeout artifact を検証
- [ ] 4-3. unresolved risks と handoff を確認

### Phase-5 Ship Gate

- [ ] 5-1. `make verify-il`
- [ ] 5-2. `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [ ] 5-3. `ci-self up --ref "$(git branch --show-current)"`
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
