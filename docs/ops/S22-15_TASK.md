
S22-15 TASK

S22-15: 1% 🟡 (WIP)

ルール: exit禁止 / set -e禁止 / 例外停止禁止 / 重処理禁止（分割）
ログ: .local/obs に “真実だけ” を残す（SKIP理由は必ず1行）

00 Preflight

 main 最新化 / prune 済み（obsに記録）

 作業ブランチ作成（衝突回避ループ）

 docs/ops の STATUS に S22-15 が 1% で載っている

01 Implement: docs_ops_doctor.py

 scripts/ops を作成（無ければ）

 doctor を追加

 実行して OK/WARN/ERROR が出ること（停止しないこと）

02 Implement: gh_ruleset_doctor.sh

 gh が無い環境は SKIP で落ちない

 rulesets JSON / check-runs JSON を obs に保存

 required_status_checks の “未観測context” を WARN で列挙

 未観測が出た時だけ直近Nコミット追観測（N小さめ）

03 Docs

 docs/ops/RULESET_GUARD.md 追加（運用の型を固定）

04 Validate (light)

 docs_ops_doctor 実行（ERRORが無い）

 gh_ruleset_doctor 実行（WARNが出たら、対処メモを残す）

05 Commit/Push/PR

 差分がある時だけ commit（無駄コミット禁止）

 push

 PR 作成（このフェーズは 1PR で閉じる）

99 Closeout (merge後)

 S22-15 を 100% ✅ に（TASK/STATUS）
