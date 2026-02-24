# S22-10 Blocker Fix (milestone_required) PLAN
Last Updated: 2026-02-24

## 目的
PR #89 / #90 の `milestone_required` を確実に解除し、#89 → #90 の順で merge-commit で閉じる。
絶対：exit/例外停止/終了コード制御なし。重い処理は分割。ログは OK/ERROR/SKIP。

## STATE
STOP = 0
ROOT = git repo root
OBS = .local/obs/s22-10_blocker_<UTC>
PRS = [89, 90]
TITLE = S22-10
OWNER/REPO = mt4110/maakie-brainlab

## ALGO

### Kickoff
if ROOT missing → print ERROR → STOP=1
else OBS 作成 → print OK

### Snapshot（軽い観測）
for pr in PRS:
  try: gh pr view で milestone/title/branch/checks を観測
  catch: ERROR をログして continue

if 両PRとも failing が milestone_required 以外も含む → 後で個別対応（ただし今回は milestone が主犯）

### Ensure milestone exists（作成 or 取得）
try: milestones 一覧から TITLE と一致する number を探す
if found → OK (MID)
else:
  try: create milestone TITLE
  if created → OK (MID)
  else → ERROR & STOP=1（以降は進まない：嘘を付かない）

### Apply milestone to PRs（2PR共通）
if STOP=0 and MID exists:
  for pr in PRS:
    try: gh api PATCH issues/pr milestone=MID
    catch: ERROR（ただし止めない）→ continue
    confirm: gh pr view で milestone title を再観測
  else SKIP

### Re-run / Wait checks（軽）
for pr in PRS:
  if milestone_required still FAIL:
    try: workflow run を rerun（該当 branch の最新 run のみ）
    catch: SKIP（手動 rerun に切り替え）
  else OK

### Merge sequence（絶対順）
if #89 checks OK:
  run ops/pr_merge_guard.sh 89 (dry) → OKなら --merge
else ERROR（ここで止める＝次へ進まない）

after #89 merged:
#90 が STATUS を “Merged PR #89” と書いているなら、真実になったかを観測
if still untrue → #90 を更新コミット（STATUS修正）→ push → checks 待ち
then ops/pr_merge_guard.sh 90 → --merge

### Closeout
milestone close（必要なら）→ best-effort（失敗はSKIP）
local cleanup は別カプセル（重くしない）
