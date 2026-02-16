# S19 Plan — PR Body Fixer (S19-01 + S19-02)

## Status
Done (merged)

## Goal
PR本文（Body）の整形・自動修正を安定化し、PR儀式の一部として再現性ある状態にする。

## Result (facts)
- S19-02 merged ✅（PR #59）
- main で `go test ./...` PASS ✅
- main で `go run cmd/reviewpack/main.go submit --mode verify-only` PASS ✅

## Known Debt (now resolved by S20)
- S19_PLAN / S19_TASK がテンプレのままだと「全体図どれ？」で迷子になる → S20で入口（ROADMAP）を追加し固定する
