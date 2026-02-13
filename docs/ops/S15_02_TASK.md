# S15-02 TASK — Fail fast on MkdirAll errors

注意（このタスク内のシェル例に限る）：このドキュメント中のシェルスニペットでは set -euo pipefail を使用しないこと（リポジトリ内の実スクリプトの方針とは無関係）。

## 0) Preflight
- [x] cd "$(git rev-parse --show-toplevel)"
- [x] git status -sb が clean
- [x] git switch s15-02-mkdirall-hardening-v1

## 1) 失敗箇所およびCopilot指摘の修正
- [x] FIX: `submit.go` の `log.Fatal` 複数引数によるビルドエラーを `log.Fatalf` へ修正
- [x] REF: `utils.go` に `ensureDir`, `generatePlaceholderLog` ヘルパーを導入（error返し）
- [x] FIX: `submit.go` / `pack.go` をヘルパー利用に差し替え、診断メッセージに path を追加
- [x] FIX: `diff_test.go` の `os.WriteFile` エラー握りつぶしを全件 `t.Fatal` 化

## 2) テスト追加・更新
- [x] UPDATE: `mkdir_test.go` をヘルパー関数の fail-fast 実証テストへ作り替え
- [x] VERIFY: 既存ファイルによるディレクトリエラーが path 込みで検出されることを確認

## 3) ドキュメント同期
- [x] UPDATE: `S15_02_PLAN.md` をヘルパー利用＋Fail-Fast方針に更新
- [x] UPDATE: `S15_02_TASK.md`（本ファイル）を完了状態へ更新

## 4) ローカルゲート
- [x] `go test ./...` PASS
- [x] `make ci-test` PASS

## 5) commit / push / PR
- [x] git diff で余計な変更がないことを確認
- [x] git add -A
- [x] git commit -m "fix(s15-02): harden mkdirall fail-fast + test/doc alignment"
- [x] git push -u origin s15-02-mkdirall-hardening-v1
- [x] gh pr create --fill
