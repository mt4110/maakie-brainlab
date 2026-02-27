# S17-00 TASK（Kickoff）

## Safety Snapshot
- [x] `cd "$(git rev-parse --show-toplevel)"; git status -sb`
- [x] `git rev-parse --abbrev-ref HEAD`
- [x] `git log -1 --oneline --decorate`

## Author docs
- [x] Create `docs/ops/S17_PLAN.md`
- [x] Create `docs/ops/S17_TASK.md`
- [x] Create `docs/ops/S17-00_PLAN.md`
- [x] Create `docs/ops/S17-00_TASK.md`

## Gates（clean tree）
- [x] `make test`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`

## Commit（atomic）
- [x] `git add docs/ops/S17*.md docs/ops/S17-*.md`
- [x] `git commit -m "chore(docs): kickoff S17 IL Contract v1 (milestones + plan/task)"`

## Push & PR
- [x] `git push -u origin HEAD`
- [x] `gh pr create --base main --head "$(git rev-parse --abbrev-ref HEAD)" --fill`
