# S20 Plan — Ops Roadmap Index v1 (docs/ops 総合目次)

## Status
- Draft → Implement → Verify → Done

## Goal
docs/ops に「入口（地図）」を1枚置き、以後 **“どこを見ればいいか” を二度と迷わない状態**に固定する。

## Background / Problem
- Sxx が増えるほど、参照起点が散って迷子になりやすい
- 特に「シリーズ全体図（Sxx_PLAN）」「実行（Sxx_TASK）」「個別フェーズ（Sxx-yy）」の対応が頭の中にしか無い
- S19 は実質完了だが、S19_PLAN / S19_TASK がテンプレ残骸のままで迷子ポイントになっている

## Scope (What we do)
- `docs/ops/ROADMAP.md` を新規追加（入口1枚）
- ROADMAP の最上段に「どの doc を見れば何が分かるか」を固定
- S15〜S19 をリンク付きで俯瞰（完了/進行中/テンプレ残骸あり を正直に）
- S19_PLAN / S19_TASK をテンプレ→実態に更新（迷子の根を抜く）
- 今後の運用ルールを明文化：新しいS開始時に ROADMAP.md へ1行追加

## Non-Goals (What we do NOT do)
- 過去ドキュメントの全面リライト
- ファイル名の大規模改名
- 自動生成ツールの作り込み（まずは手書きSOTで固定）

## Deliverables (Artifacts)
- `docs/ops/ROADMAP.md` (new)
- `docs/ops/S20_PLAN.md` / `docs/ops/S20_TASK.md` (this series)
- Update: `docs/ops/S19_PLAN.md` / `docs/ops/S19_TASK.md` (template → reality)

## Acceptance Criteria
- ROADMAP.md が入口として機能し、参照起点が1つになる
- ROADMAP.md のリンクが相対パスで解決できる（壊れていない）
- S19_PLAN / S19_TASK が実態に合っている（S19-02 merged / main gate PASS を明記）
- `file://` を混ぜない
- `go test ./...` が PASS
- `reviewpack submit --mode verify-only` が PASS（いつもの健康診断）

## Evidence / Gates
- `go test ./...`
- `go run cmd/reviewpack/main.go submit --mode verify-only`
- PR 作成 → main merge 後、必要なら main で再実行して PASS を確認

