# S19-02_PLAN

## 背景（S19-01の延長）

現状の pr_body_required.yml は github-script(JS) を内包している
長期運用では 言語混在が保守コスト・事故率を上げる
“根絶”の最終形は Go単一ロジック（ローカル/CIで同じ挙動）

## 目的（完了条件）

*   CI保険が cmd/prbodyfix を呼ぶ（JSを排除）
*   ローカルでも cmd/prbodyfix を実行できる（同じロジック）
*   冪等：同じPRに対し 2回連続で実行しても2回目は更新しない
*   fork PR は権限不足を検出して SKIP PASS

## 設計（Invariants）

*   本文整形ロジックは純関数として internal/prbodyfix に隔離する
*   Normalize() は trimしない（行除去のみ）
*   empty判定だけ strings.TrimSpace() を使う
*   trailing newline は EnsureTrailingNewline() を1回だけ
*   CI側の Evidence は 不変情報だけ
    *   HeadSHA（PRの head sha）
    *   Run（Actions run URL）
*   更新は desired != current のときだけ（冪等）

## Pseudocode（止まらない型）

```go
try:
  repo_root = git rev-parse --show-toplevel OR (CIなら不要)
catch:
  # CIでもローカルでも動くように、gitが無いなら repo解決を別ルートへ
  continue

# 0) 入力源の決定（CI event / local args）
if env(GITHUB_EVENT_PATH) exists:
  try read event JSON
  prNumber = event.pull_request.number
  owner/repo = event.repository.owner.login / event.repository.name
  headSHA = event.pull_request.head.sha
  baseSHA = event.pull_request.base.sha
  isFork = (event.pull_request.head.repo.full_name != owner+"/"+repo)
else:
  # local mode
  require --pr
  owner/repo = (arg --repo) else parse from `git remote get-url origin`
  headSHA/baseSHA = optional (APIで取得)

if isFork:
  skip "fork PR detected; no write permission"; PASS

# 1) GitHub API client
token = env(GITHUB_TOKEN) else env(GH_TOKEN) else try("gh auth token")
if token empty:
  error "missing token"; STOP

# 2) Fetch current PR body (source-of-truth)
try GET /repos/{owner}/{repo}/pulls/{prNumber}
catch error: error "cannot fetch PR"; STOP

currentBody = pr.body or ""

# 3) Fetch template (best-effort, pinned)
try GET /repos/{owner}/{repo}/contents/.github/pull_request_template.md?ref={baseSHA}
catch: template=""

# 4) Normalize
desired = Normalize(currentBody, template, headSHA, runURL)
# Normalize rules:
# - strip sentinel lines (trimStart + HasPrefix)
# - if empty after strip:
#     - use template (after strip) if non-empty
#     - else minimal body with HeadSHA+Run URL
# - ensure evidence section exists
# - ensure trailing newline exactly 1

# 5) Apply
if desired == currentBody:
  PASS (idempotent)
else:
  try PATCH /repos/{owner}/{repo}/pulls/{prNumber} body=desired
  catch: error "update failed"; STOP
  PASS
```

## 実装ファイル（固定パス）

*   cmd/prbodyfix/main.go
*   internal/prbodyfix/normalize.go
*   internal/prbodyfix/github.go
*   internal/prbodyfix/normalize_test.go
*   .github/workflows/pr_body_required.yml
