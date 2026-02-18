# S21-03 PLAN

## Scope
S21-03 Ops Hygiene — Milestone Event Autorecheck

## Problem
`gh run rerun` が過去の `pull_request` event payload（化石）を再生する場合がある。
その結果、Milestone を後から付けても payload 上は `missing milestone` のままになり、rerunしても失敗が再現する。

## Goal
- Milestone 変更で `milestone_required` が自動再判定される（close/reopen の儀式を廃止）
- 判定は event payload ではなく GitHub API で「現在のPR状態」を取得する（rerun罠を根絶）

## Deliverables
- docs/ops/S21-03_PLAN.md
- docs/ops/S21-03_TASK.md
- docs/ops/PR_WORKFLOW.md（追記）
- docs/ops/STATUS.md（S21-03 行: 0%）
- .github/workflows/milestone_required.yml
  - pull_request.types に milestoned / demilestoned を追加（列挙固定）
  - milestone判定を API による現在PR取得へ移行（payload依存排除）
- (if exists) .github/workflows/milestone_advisory.yml（同様）

## Invariants (Non-Negotiable)
- 判定は event payload を信用しない。必ず GitHub API で現在の PR を取得する。
- `pull_request.types` は “必要イベントを固定列挙” する（欠けさせない）。
- 重い検証は分割し、最終段だけ任意にする（ターミナル/CIの健康優先）。

## Design (Pseudo-code)
if event in {opened, reopened, synchronize, edited, labeled, unlabeled, milestoned, demilestoned}:
  pr = fetch_current_pr_via_github_api(pr_number)
  milestone = pr.milestone

  if milestone exists:
    milestone_required = PASS
  else:
    milestone_required = FAIL  (expressed as check result)

## Evidence
- Diff scope: workflow + docs + plan/task + status のみ
- PR上で以下を確認できるログ:
  - Milestone未設定 → milestone_required が FAIL
  - PRにMilestoneを後付け → milestoned で自動再実行され PASS になる（rerun不要）
  - Milestoneを外す → demilestoned で自動再実行され FAIL になる
