# S21-04 PLAN

## Scope
S21-04 Milestone Autofill & Merge Guard

## Goal
- Milestoneの設定漏れを機械的にゼロにする（Autofill）
- マージ操作をカプセル化し、必須チェック漏れによる事故をゼロにする（Merge Guard）

## Deliverables
- .github/workflows/milestone_autofill.yml
- ops/pr_merge_guard.sh
- docs/ops/S21-04_PLAN.md
- docs/ops/S21-04_TASK.md
- docs/ops/PR_WORKFLOW.md（追記）
- docs/ops/STATUS.md（S21-04 行追加）

## Invariants (Non-Negotiable)
- Merge Guard はローカル実行のみとし、GitHub上での強制（Ruleset）に依存しない。
- Autofill は「人間が忘れても機械が補完する」思想で動く。

## Design (Pseudo-code)
### Milestone Autofill
```javascript
if (pr.milestone) return; // already set
if (headRef.match(/S(\d+)/) || title.match(/S(\d+)/)) {
  const milestone = findMilestone(match);
  if (milestone) setMilestone(pr, milestone);
}
```

### Merge Guard
```bash
check_git_repo()
check_pr_number()
check_milestone_set()
check_checkrun_success("milestone_required")
check_all_checks_passed()
if (dry_run) print_ok()
else merge_pr()
```
