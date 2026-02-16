# S20-03 Task — Eval Wall v1 impl

## Progress
- [x] 0% Start
- [x] 10% Plan/Task fixed
- [x] 30% Dataset skeleton added (repo)
- 60% Run artifacts writer implemented (local)
- 80% Taxonomy wiring + summary aggregation
- 90% Gates pass
- 100% PR merged

## C0: Safety Snapshot
- [x] `git status -sb` clean（dirtyなら commit 先）
- [x] `git grep -nE 'file:/{2}|/U[s]ers/' -- docs data eval || true`

## C1: Dataset skeleton (repo / fixed inputs)
- [x] `data/eval/datasets/<dataset_id>/` を追加
- [x] `cases.jsonl`（必須）+ `dataset.meta.json`（必須）
- [x] `dataset_id` は凍結ルール（kebab + vNNNN）に沿う

## C2: Run artifacts writer (local / fixed outputs)
- [ ] `.local/rag_eval/runs/<run_id>/` を生成
- [ ] 必須ファイル: `run.meta.json`, `results.jsonl`, `summary.json`
- [ ] 推奨ファイル: `command.txt`（実行コマンドを1行保存）

## C3: Failure taxonomy wiring (fixed labels)
- [ ] `results.jsonl` に `status` と `failure_code` を必ず出す
- [ ] `summary.json` に `failure_code` 集計を出す（名称は凍結）
- [ ] “1ケース=1 failure_code” を維持（v1は単純集計）

## C4: ROADMAP update
- [x] `docs/ops/ROADMAP.md` の S20 セクションに S20-03 を追記

## C5: Gates
- [ ] `go test ./...`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`

## C6: PR
- [ ] `git push -u origin HEAD`
- [ ] PR作成（`./ops/pr_create.sh` or `gh pr create --fill`）
- [ ] CI green → merge
