# S15-10 TASK (S15-09/10 - 1PR)

## 0. Preflight

- [x] S15-09 gate PASS 済み（Task.mdに証拠あり）
- [x] bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'

## 1. Implementation (Part B: Verification Hardening)

- [x] `internal/reviewpack/verify.go` / `evidence.go` / `utils.go` の修正
- [x] `logs/raw/10_git_log.txt` / `30_make_test.log` / `40_self_verify.log` の存在チェックを実装
- [x] rawログ（10/11/40）に同名 `.sha256` サイドカーが生成されることを確認
- [x] Evidence marker 判定の強化（必須ログが揃っていることを確認）

## 2. Verification (Final Gate)

- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'
- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'
- [x] 成功観測点: PASS: Verify OK が出力されること

## 3. Evidence

- [x] PASS要点 / bundle名 / SHA256 を末尾に記録
