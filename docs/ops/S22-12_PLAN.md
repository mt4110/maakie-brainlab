# S22-12: Stale Milestone Check Elimination

## Problem

`milestone_autofill` が `GITHUB_TOKEN` で milestone を付与しても、GitHub の仕様により
`milestone_required` workflow は再起動しない。結果として required check が stale のまま残り、
人間が手動 rerun する必要がある。

## Solution

`milestone_autofill` → `workflow_dispatch` → `milestone_required` の明示的再実行チェーン。

### Changes

1. **`milestone_required.yml`** — `workflow_dispatch` トリガ追加（`inputs.pr_number`）
2. **`milestone_autofill.yml`** — dispatch step + 監査ログ + `actions: write` permission
3. **`s22_milestone_autofill.yml`** — 重複のため削除

### Verification

- milestone なしで PR 作成 → autofill → dispatch → milestone_required が自動再走 → 手動 rerun ゼロ
