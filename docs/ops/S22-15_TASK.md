
S22-15 TASK

S22-15: 100% ✅ (Merged PR #98 / commit 2b8df7b)

ルール: exit禁止 / set -e禁止 / 例外停止禁止 / 重処理禁止（分割）
ログ: .local/obs に “真実だけ” を残す（SKIP理由は必ず1行）

00 Preflight

- [x] main 最新化 / prune 済み（obsに記録）
- [x] 作業ブランチ作成（衝突回避ループ）
- [x] docs/ops/ STATUS に S22-15 が 50% で載っている

01 Implement: docs_ops_doctor.py

- [x] scripts/ops を作成（無ければ）
- [x] doctor を追加
- [x] 実行して OK/WARN/ERROR が出ること（停止しないこと）

02 Implement: gh_ruleset_doctor.sh

- [x] gh が無い環境は SKIP で落ちない
- [x] rulesets JSON / check-runs JSON を obs に保存
- [x] required_status_checks の “未観測context” を WARN で列挙
- [x] 未観測が出た時の Hint 表示（Nコミット追観測は descope/軽量化）

03 Docs

- [x] docs/ops/RULESET_GUARD.md 追加（運用の型を固定）

04 Validate (light)

- [x] docs_ops_doctor 実行（ERRORが無い）
- [x] gh_ruleset_doctor 実行（WARNが出たら、対処メモを残す）

05 Addendum: Pro Ops Pack (4-9, Local Only)
- [x] 4-A: Extract ruleset ID from latest audit log [/]
- [x] 4-B: Re-audit with PR head SHA (if available)
- [x] 4-C: Self-audit for banned tokens (exit/SystemExit)
- [x] 5: Pin SOT (write-sot) and commit
- [x] 6: Generate/Apply ghost prune candidate (APPLY_SOT=1)
- [x] 7: Sync SOT to Ruleset (APPLY_SYNC=1 + Double-lock)
- [x] 8: Automated PR creation
- [x] 9: Closeout (100% status update and commit)

99 Closeout (merge後)
- [x] S22-15 を 100% ✅ に（TASK/STATUS）
