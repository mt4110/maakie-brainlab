# S17-03 Task — Run Always 1h Scheduled Failure Triage

## Step 0: Safety Snapshot（混ぜない）
- [x] cd "$(git rev-parse --show-toplevel)"
- [x] git status -sb
- [x] STOP: dirty なら混ぜない（stash / commit / 捨てるを先に）

## Step 1: 失敗runを特定（schedule を優先）
- [x] 最近の runs を一覧（まず俯瞰）: `gh run list -w "run_always_1h.yml" -L 30`
- [x] 失敗Runを1つ選ぶ（main / schedule / failure）: `22027626252`
- [x] 失敗ログだけ（強い：まずこれ）: `gh run view 22027626252 --log-failed`

## Step 1.1: 証拠回収（保存して監査可能にする）
- [x] 証拠置き場作成: `mkdir -p docs/evidence/s17-03`
- [x] Runメタデータ保存: `docs/evidence/s17-03/run_22027626252.json`
- [x] 失敗ログ保存: `docs/evidence/s17-03/log_failed_22027626252.txt`

## Step 2: 作業ブランチ（main を汚さない）
- [ ] git switch main
- [ ] git pull --ff-only
- [ ] git fetch -p origin
- [ ] git switch -c s17-03-run-always-1h-fix-v1

## Step 3: ローカル再現（まず repo のスクリプトを信じる）
- [ ] ローカル実行: `bash ops/run_always_1h.sh`
- [ ] IF（ローカル再現しない）→ CI-only差分を証拠化

## Step 4: 最小修正（変更面積を最小に）
- [ ] 診断ログ追加
- [ ] 修正適用
- [ ] 再発防止策

## Step 5: Gate（嘘をつかない）
- [ ] make test
- [ ] go run cmd/reviewpack/main.go submit --mode verify-only
- [ ] git status -sb（意図した差分だけか確認）

## Step 6: Docs更新（Plan/Task + 必要なら runbook）
- [ ] docs/ops/S17-03_PLAN.md 追記
- [ ] docs/ops/S17-03_TASK.md 追記

## Step 7: コミット → PR
- [ ] git add -A
- [ ] git commit -m "fix(s17-03): stabilize scheduled run_always_1h and harden diagnostics"
- [ ] git push -u origin s17-03-run-always-1h-fix-v1
- [ ] gh pr create --fill
