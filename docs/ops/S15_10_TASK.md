# S15-10 TASK (S15-09/10 - 1PR)

## 0. Preflight

- [ ] S15-09 gate PASS 済み（Task.mdに証拠あり）
- [ ] bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'

## 1. Implementation (Part B: Verification Hardening)

- [ ] `internal/reviewpack/verify.go` の修正
- [ ] `logs/raw/10_git_log.txt` と `logs/raw/40_self_verify.log` の存在チェックを実装
- [ ] Evidence marker 判定の強化（hasGoTest, hasUnittest, etc）

## 2. Verification (Final Gate)

- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'
- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'
- [ ] 成功観測点: PASS: Verify OK が出力されること

## 3. Evidence

- [ ] PASS要点 / bundle名 / SHA256 を末尾に記録
