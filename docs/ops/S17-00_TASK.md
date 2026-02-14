# S17-00 TASK（Kickoff）

## Safety Snapshot
- [ ] `cd "$(git rev-parse --show-toplevel)"; git status -sb`
- [ ] `git rev-parse --abbrev-ref HEAD`
- [ ] `git log -1 --oneline --decorate`

## Author docs
- [ ] Create `docs/ops/S17_PLAN.md`
- [ ] Create `docs/ops/S17_TASK.md`
- [ ] Create `docs/ops/S17-00_PLAN.md`
- [ ] Create `docs/ops/S17-00_TASK.md`

## Gates（clean tree）
- [ ] `make test`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`

## Commit（atomic）
- [ ] `git add docs/ops/S17*.md docs/ops/S17-*.md`
- [ ] `git commit -m "chore(docs): kickoff S17 IL Contract v1 (milestones + plan/task)"`

## Push & PR
- [ ] `git push -u origin HEAD`
- [ ] `gh pr create --base main --head "$(git rev-parse --abbrev-ref HEAD)" --fill`
