# S22-12 TASK: Stale Milestone Check Elimination

## Checklist

- [ ] 01. `milestone_required.yml` に `workflow_dispatch` 追加 + dispatch-aware PR fetch
- [ ] 02. `milestone_autofill.yml` に dispatch step + 監査ログ + `actions: write` 追加
- [ ] 03. `s22_milestone_autofill.yml` 削除（重複）
- [ ] 04. `STATUS.md` 更新
- [ ] 05. YAML 構文検証
- [ ] 06. PR 作成 → CI green → merge

## DoD

- `milestone_autofill` が milestone 付与後、`milestone_required` を `workflow_dispatch` で自動再実行
- dispatch 失敗時、milestone_autofill のログと Summary に `ERROR:` が 1 行残る（pr/head_sha/status/msg を含む）
- 手動 rerun ゼロで PR が merge 可能状態になる
