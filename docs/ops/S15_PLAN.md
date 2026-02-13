# S15-00: Pack Delta Report v1 — baseline(main) generation uses PR reviewpack binary

## Goal
CI の Pack Delta で pack_delta=2 が出る原因（baseline側で --skip-test 未定義）を潰し、**baseline生成も diff 実行も “PR側でビルドした reviewpack バイナリ”**を使って安定化する。

## Background / Root Cause

baseline(worktree=origin/main) 側で go run ... submit --skip-test を実行すると、origin/main には --skip-test が無く flag provided but not defined 等で失敗しうる。その結果 pack_delta=2（hard failure）になり、Final Aggregation が正しく落とす。

## Non-goals

- pack_delta=1（diff found）で CI を落とす（差分は情報）。
- GitHub 外部依存を増やす。
- worktree をやめる（現状の isolation 維持）。

## Contract

10_status.tsv の pack_delta は次を満たす：
- 0: OK（no diff or diff found treated as info）
- 1: OK（diff found - info）
- 2: Hard error（CI fail 対象）

Final Aggregation は pack_delta=2 のみ fail（他は従来通り）。

## Implementation Strategy

plan:
- if .github/workflows/verify_pack.yml が存在しない → error STOP（パス違い）
- if Pack Delta Report step が存在しない → error STOP（S15未導入）
- for patch_targets in ["Pack Delta Report", "pack_delta", "main-worktree"]:
    - 探索で該当ブロックを特定
    - 見つけたら break
    - 見つからなければ continue
- 最終的に見つからない → error STOP（曖昧な修正はしない）

Main fix（唯一の正攻法）:
- PR workspace で go build し、runner.temp に reviewpack バイナリを置く。
- baseline(worktree) では go run を使わず、そのバイナリで submit --skip-test を実行。
- diff も同バイナリを使う（実行器の統一）。

Init safety（ゾンビ対策は同一run内の二次防止）:
- Init CI で .local/ci/10_status.tsv を必ず truncate（: >）。
- ただし前run持ち越し対策が目的ではない（runnerは基本クリーン）。

## Gates
- if go build -o "$REVIEWPACK_BIN" ./cmd/reviewpack が失敗 → error STOP（pack_delta=2 を記録）
- if baseline bundle の生成が失敗 → error STOP（pack_delta=2）
- if bundle count が PR=1 / MAIN=1 でない → error STOP（pack_delta=2）
- if diff(JSON) の exit code が 2 → error STOP（pack_delta=2）

## Docs / Ops
- S15_TASK.md の手順に「PR reviewpack binary を作って baseline で使う」項目を追加。
- 変更点を audit-friendly に1行で残す。

## Future Steps (S15-07..10)
- [S15_07_PLAN.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15_07_PLAN.md)
- [S15_08_PLAN.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15_08_PLAN.md)
- [S15_09_PLAN.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15_09_PLAN.md)
- [S15_10_PLAN.md](file:///Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S15_10_PLAN.md)
