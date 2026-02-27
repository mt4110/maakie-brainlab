# S29-01-S29-10 THREAD v2 TASK — WARN_ONLY Waiver Burn-down

Last Updated: 2026-02-27

## Progress

- S29-01-S29-10 v2: 0% (planning kickoff)

## Current Facts

- S29 v1 は closeout `PASS`、ただし readiness は `WARN_ONLY`。
- v2 は waiver削減と実運用接続の再実証フェーズ。
- 進捗SOTは本TASKとPR body（`STATUS.md`は非SOT）。

## Ritual 22-16-22-99

- PLAN: `docs/ops/S29-01-S29-10-THREAD-V2_PLAN.md`
- DO: チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: コマンド結果を PR body に固定

## CI Budget Rule

- 原則: `ci-self` は ship 直前の1回のみ。
- 例外: 失敗時のみ修正後1回再実行（合計2回まで）。

## Checklist

### Phase-1 Design Freeze

- [ ] 1-1. S29-10 Exit v2 条件と READY 判定目標を固定
- [ ] 1-2. v1 WARN要因（notify/soak/taxonomy/recovery）を実装要求へ分解
- [ ] 1-3. 変更対象（script/test/evidence）を確定
- [ ] 1-4. PR body 記録テンプレート（OK/WARN/ERROR/SKIP）を更新

### Phase-2 Implementation Batch

- [ ] 2-1. S29-01 success-rate SLO v2 差分を実装
- [ ] 2-2. S29-02 pipeline integration v2 差分を実装
- [ ] 2-3. S29-03 notify multichannel v2（実送信前提）を実装
- [ ] 2-4. S29-04..10 連結ロジックを v2 更新

### Phase-3 Local Check Batch

- [ ] 3-1. `make ops-now`
- [ ] 3-2. `python3 -m unittest -v tests/test_s29_*.py`
- [ ] 3-3. 主要 phase コマンドの再実行

### Phase-4 End-to-End Verification

- [ ] 4-1. S29-01..S29-10 を順次実行
- [ ] 4-2. readiness / closeout artifact を検証
- [ ] 4-3. waiver / unresolved risks / handoff を検証

### Phase-5 Ship Gate

- [ ] 5-1. `make verify-il`
- [ ] 5-2. `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [ ] 5-3. `ci-self up --ref "$(git branch --show-current)"`
- [ ] 5-4. PR body を最終更新

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
