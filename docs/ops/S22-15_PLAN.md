# S22-15 PLAN
## SOT
- Prev: S22-14 = 100% ✅ (Merged PR #94 / commit e74cb10)
- Now: S22-15 = 100% ✅ (Merged PR #98 / commit 2b8df7b)

## Theme (neutral but durable)
Ops Guardrails: GitHub Ruleset required_status_checks の “幽霊context” 再発防止 + docs/ops SOT同期の監査性向上

## Goals
- GitHub Ruleset の required_status_checks を観測可能にする（幽霊checkを発見できる）
- docs/ops の SOT (STATUS.md / TASK.md) が矛盾したら即わかる
- すべて stopless: exit禁止 / 例外停止禁止 / 重処理禁止（分割）/ ログに真実だけ
- **[Addendum] Proの死角潰し: RID自動抽出 / PR head SHA監査 / SOT固定 / prune-sync自動化**

## Non-Goals
- Ruleset を API で自動編集（事故りやすいので今回はやらない）
- CI で exit code による強制fail（本プロジェクトの exit禁止運用に反するため）

## Deliverables
- scripts/ops/gh_ruleset_doctor.sh
  - rulesets を取得し required_status_checks を抽出
  - default branch の直近コミットの check-runs と照合して “未観測” を列挙
  - “未観測” が出た場合、Hint (HINT:) を表示して監査を促す（軽量・HEAD観測重視）
  - すべて .local/obs にスナップショット保存
- scripts/ops/docs_ops_doctor.py
  - docs/ops の存在・整合・進捗行を検査（ERROR/WARN/OK を print）
  - sys.exit/raise/assert なし。例外は catch して ERROR print
- docs/ops/RULESET_GUARD.md (運用Runbook)
- **ops/s22-15_ops_pack.sh (Local-only automation helper, NOT tracked in PR)**
- **ops/ruleset_required_status_checks.json (SOT)**

## Acceptance Criteria
- gh が使える環境で doctor を実行すると、(a) OK: ghost候補なし もしくは (b) WARN: 未観測context一覧 が出る
- gh が無い/認証できない環境でも、SKIP理由が1行で残り、ターミナルを落とさない
- docs_ops_doctor が docs/ops の矛盾を ERROR として列挙できる（停止はしない）

---

## Execution Pseudocode (stopless)
```text
if not in_git_repo:
  error("not in repo")
  stop

else if docs/ops missing:
  try:
    create docs/ops
  catch:
    error("cannot create docs/ops")
    stop

for each artifact in [PLAN, TASK, doctor scripts, docs]:
  if exists:
    skip("exists: ...")
    continue
  else:
    try:
      write artifact
    catch:
      error("write failed: ...")
      stop

try:
  run docs_ops_doctor
catch:
  error("doctor crashed (should not)")
  stop

if gh_available and gh_authed:
  try:
    run gh_ruleset_doctor
  catch:
    error("ruleset doctor crashed (should not)")
else:
  skip("gh not available or not authed")

if everything ready:
  commit + push + PR
else:
  stop (leave logs)

