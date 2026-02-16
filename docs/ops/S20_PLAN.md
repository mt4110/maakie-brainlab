# S20 Plan — Ops Roadmap Index v1 (docs/ops 総合目次)

## Status
- Draft → Implement → Verify → Done

## Goal
docs/ops に「入口（地図）」を1枚置き、以後 “どこを見ればいいか” を二度と迷わない状態に固定する。

## Background / Problem
- Sが増えるほど参照起点が散って迷子になりやすい
- 「シリーズ全体図（Sxx_PLAN）」「実行（Sxx_TASK）」「個別フェーズ（Sxx-yy）」の対応が頭の中にしか無い
- S19 は実質完了だが、S19_PLAN / S19_TASK がテンプレ残骸のままで迷子ポイントになっている

## Scope (What we do)
- `docs/ops/ROADMAP.md` を追加（入口1枚）
- ROADMAP 最上段に「どの doc を見れば何が分かるか」を固定
- S15〜S19 をリンク付きで俯瞰（完了/進行中/テンプレ残骸あり を正直に）
- S19_PLAN / S19_TASK をテンプレ→実態に更新（迷子の根を抜く）
- 運用ルールを明文化：新しいS開始時に ROADMAP.md へ1行追加

## Non-Goals
- 過去ドキュメントの全面リライト
- ファイル名の大規模改名
- 自動生成ツールの作り込み（まずは入口を固定して勝つ）

## Deliverables
- `docs/ops/ROADMAP.md` (new)
- `docs/ops/S20_PLAN.md` / `docs/ops/S20_TASK.md`
- Update: `docs/ops/S19_PLAN.md` / `docs/ops/S19_TASK.md`

## Acceptance Criteria
- ROADMAP.md が入口として機能し、参照起点が1つになる
- ROADMAP.md のリンクが実在ファイルに向く（壊れていない）
- S19_PLAN / S19_TASK が実態に合っている（S19-02 merged / main gate PASS を明記）
- `file://` を混ぜない
- `go test ./...` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

## Evidence / Gates
- `go test ./...`
- `go run cmd/reviewpack/main.go submit --mode verify-only`
