# S28-01-S28-10 THREAD v5 TASK — Slow-Paced One-Pass Delivery

Last Updated: 2026-02-27

## Progress

- S28-01-S28-10 v5: 100% (一気通貫実行・ローカル検証・verify-il・ci-self green まで完了)

## Current Facts

- v4 までで S28 機能は完成済み（readiness WARN_ONLY / closeout PASS）。
- v5 では docs 運用改善（Phase追加 / CI budget明文化）を1バッチで反映。
- 実行結果: `S28-09=WARN_ONLY`, `S28-10=PASS`, `waived_hard_count=4` を再確認済み。
- `ci-self` は初回 `No ref found`（remote branch未作成）後、branch pushして再実行し green 完了。

## Non-negotiables

- Ritual `22-16-22-99` を遵守（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking のまま。
- `STATUS.md` を進捗SOTに使わない（TASK + PR bodyに固定）。
- PR作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行して全green確認。
- 小分けCIを連打せず、ship直前にまとめて最終ゲートを通す。

## CI Budget Rule (v5)

- 原則: `ci-self` は Phase-5 の1回のみ。
- 例外: 1回目失敗時のみ、ローカル修正後に再実行1回（合計2回まで）。
- Phase-1..4 では CI を実行せず、ローカル検証で不具合を先に潰す。

## Checklist

### Phase-1 Design Freeze (new / 60m target)

- [x] 1-1. S28-10 Exit から逆算した設計順序を固定
- [x] 1-2. 実装対象と非対象（今回は運用テンポ改善中心）を固定
- [x] 1-3. CI budget（最終1回 + 失敗時再試行1回まで）を固定
- [x] 1-4. PR body 記載フォーマット（OK/WARN/ERROR/SKIP）を先に下書き

### Phase-2 Implementation Batch

- [x] 2-1. 必要なコード変更を1バッチで実装（今回は docs/ops + evidence 更新）
- [x] 2-2. 変更が docs-only の場合は理由を明記して確定（機能はv4で完了済み）
- [x] 2-3. 変更ファイル契約（S28 script/test/doc）を最終確認

### Phase-3 Local Check Batch

- [x] 3-1. `make ops-now`
- [x] 3-2. `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`
- [x] 3-3. `python3 -m unittest -v tests/test_s28_closeout.py`
- [x] 3-4. 必要なら追加テストを同一バッチで実行（N/A: docs運用更新中心のため追加不要）

### Phase-4 End-to-End Verification

- [x] 4-1. `make s28-slo-readiness-v2`
- [x] 4-2. `make s28-closeout`
- [x] 4-3. readiness / closeout artifact の整合確認

### Phase-5 Ship Gate

- [x] 5-1. `make verify-il`
- [x] 5-2. `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [x] 5-3. `ci-self up --ref "$(git branch --show-current)"`（初回失敗後の再試行1回でgreen）
- [x] 5-4. PR body へ実行コマンドと結果を固定

## Validation Commands

- `make ops-now`
- `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`
- `python3 -m unittest -v tests/test_s28_closeout.py`
- `make s28-slo-readiness-v2`
- `make s28-closeout`
- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は PR body に固定する。
- 各 phase で最低1行の `OK:/WARN:/ERROR:/SKIP:` を残す。
- `SKIP` は理由を1行で明示する。

## PR Body Draft (Run Log)

- `OK: make ops-now`（task_file=v5 / progress 12% at run time）
- `OK: python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`（9 tests, all green）
- `OK: python3 -m unittest -v tests/test_s28_closeout.py`（3 tests, all green）
- `WARN: make s28-slo-readiness-v2`（readiness=WARN_ONLY, reason=SOFT_SLO_WARN, waived_hard_count=4）
- `OK: make s28-closeout`（status=PASS, readiness=WARN_ONLY）
- `OK: make verify-il`（runtime entrypoint / smoke / suite all green）
- `ERROR: ci-self up --ref "$(git branch --show-current)"`（HTTP 422 No ref found for branch）
- `OK: git push -u origin ops/S28-01-S28-10`（remote branch作成）
- `OK: ci-self up --ref "$(git branch --show-current)"`（verify workflow #110 green）
- `SKIP: pr_checks`（reason=pr_not_found_for_branch）
