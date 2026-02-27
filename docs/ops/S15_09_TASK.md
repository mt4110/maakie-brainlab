# S15-09 TASK (S15-09/10 - 1PR)

## 0. Preflight

- [x] bash -lc 'cd "$(git rev-parse --show-toplevel)"; git status -sb'
- [x] check branch: s15-09-10-fixpack-v1

## 1. Implementation (Part A: Submission Hardening)

- [x] `internal/reviewpack/repo.go` 内の `findLatestEvalResult` を修正
- [x] `runPreflightChecks` に `file[:]//` URL 検知ロジックを追加
- [x] `make test` で基本動作確認

## 2. Verification

- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'
- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'
- [x] 成功観測点: PASS: Verify OK が出力されること

## 3. Evidence

- [x] 実行コマンドと結果をTask末尾に記録
