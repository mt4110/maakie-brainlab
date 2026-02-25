
S22-15 TASK

S22-15: 100% ✅ (Merged)

ルール: exit禁止 / set -e禁止 / 例外停止禁止 / 重処理禁止（分割）
ログ: .local/obs に “真実だけ” を残す（SKIP理由は必ず1行）

00 Preflight

- [x] main 最新化 / prune 済み（obsに記録）
- [x] 作業ブランチ作成（衝突回避ループ）
- [x] docs/ops の STATUS に S22-15 が 1% で載っている

01 Implement: docs_ops_doctor.py

- [x] scripts/ops を作成（無ければ）
- [x] doctor を追加
- [x] 実行して OK/WARN/ERROR が出ること（停止しないこと）

02 Implement: gh_ruleset_doctor.sh

- [x] gh が無い環境は SKIP で落ちない
- [x] rulesets JSON / check-runs JSON を obs に保存
- [x] required_status_checks の “未観測context” を WARN で列挙
- [x] 未観測が出た時だけ直近Nコミット追観測（N小さめ）

03 Docs

- [x] docs/ops/RULESET_GUARD.md 追加（運用の型を固定）

04 Validate (light)

- [x] docs_ops_doctor 実行（ERRORが無い）
- [x] gh_ruleset_doctor 実行（WARNが出たら、対処メモを残す）

05 Commit/Push/PR

- [x] 差分がある時だけ commit（無駄コミット禁止）
- [x] push
- [x] PR 作成（このフェーズは 1PR で閉じる）

99 Closeout (merge後)

- [x] S22-15 を 100% ✅ に（TASK/STATUS）
