# S19-01_PLAN

## 目的（完了条件）

“何も考えずに” PRを作っても本文空で詰まらない

差分コミット0のときは即 STOP（理由を出す）

本文に evidence（bundle名/sha 等）が自動で入る

## A) ローカル主砲：cmd/prkit + ops/pr_create.sh（Go）

### Invariants（壊れないための約束）

*   prkit は gh pr create --fill に依存しない
*   sentinel 除去は 正規表現ではなく “行単位”（prefix一致）
*   evidence 注入は ローカル生成物から探索（無ければ最小証拠にフォールバック）
*   ターミナルは落とさない（set -e 禁止、すべて error で停止）

### Pseudocode（止まらない型）

```go
try:
  repo_root = git("rev-parse --show-toplevel")
catch error:
  error "not a git repo"; STOP

current_branch = git("rev-parse --abbrev-ref HEAD")
if current_branch == "" or current_branch == "HEAD":
  error "detached HEAD"; STOP
if current_branch == base_branch:
  error "refuse on base branch"; STOP

if git_status_porcelain != "":
  error "working tree dirty"; STOP

# upstream 解決（origin/base が無ければ base）
upstream = if git_ref_exists("origin/"+base) then "origin/"+base else base

diff_commits = git("rev-list --count "+upstream+"..HEAD")
if diff_commits == 0:
  error "STOP: diff commits=0"; STOP

title = git("log -1 --pretty=%s")

# body の素材：PR template
template = try_read(".github/pull_request_template.md")
if template == "":
  template = "## Summary\n(auto)\n\n## Evidence\n"

body = strip_sentinel_by_line_prefix(template, "PR_BODY_TEMPLATE_v1:")

evidence = find_latest_bundle(
  for paths in [
    ".local/**/review_bundle*.tar.gz",
    ".local/**/review_pack*.tar.gz",
    "./review_bundle*.tar.gz",
    "./review_pack*.tar.gz"
  ]:
    if exists(path): candidate <- stat.mtime; keep latest; break/continue
)

head_sha = git("rev-parse HEAD")
body = ensure_section(body, "## Evidence")
body = inject_lines_under_evidence(body, [
  "- HeadSHA: `...`",
  "- Bundle: `name` (if found)",
  "- SHA256: `...` (if found)",
  "- GeneratedAt: `UTC RFC3339`"
])

if trim(body) == "":
  body = minimal_body(head_sha)

# PR already exists?
if gh("pr view --json url") succeeds:
  print "PR exists"; PASS; END

gh("pr create --base base --head current --title title --body-file tmp.md")
```

## B) CI保険：.github/workflows/pr_body_required.yml

### Invariants

*   本文が空 OR sentinel 残り → “必ず” 自動修正して PASS
*   テンプレが取れなくても FAIL しない（最小本文へフォールバック）
*   fork PR は権限で編集できないので SKIP PASS（運用破綻を防ぐ）
*   連鎖イベント（body更新→edited）でも安定するように 冪等にする（変化が無ければ更新しない）

### Pseudocode（止まらない型）

```javascript
if fork_pr:
  notice "SKIP: fork"; PASS

raw = pr.body or ""

cleaned = strip_lines_where_startsWith("PR_BODY_TEMPLATE_v1:")

if trim(cleaned) == "":
  tpl = try_fetch(".github/pull_request_template.md" at base sha)
  cleaned = strip_lines_startsWith(tpl)
  if trim(cleaned) == "":
    cleaned = minimal_body(pr.head.sha, run_url)

# 最終検査（fail ではなく “補正して終わる”）
cleaned = ensure_trailing_newline(cleaned)

if cleaned != raw:
  update_pr_body(cleaned)

PASS
```

## “死角から見える副産物”（長期破綻を防ぐ小技）

*   sentinel 除去は line.includes() じゃなく line.startsWith()（誤爆防止）
*   CIは テンプレ取得失敗で FAIL しない（外部要因で詰まるのを根絶）
*   ops/pr_create.sh は --base を通せる形に（go run ... --base X create）
*   prkit の range は "upstream..HEAD" を使う（origin/base..branch みたいな曖昧さを消す）
