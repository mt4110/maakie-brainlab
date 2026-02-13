# S15-02 TASK — Fail fast on MkdirAll errors

禁止：set -euo pipefail（絶対禁止）

## 0) Preflight
- [x] cd "$(git rev-parse --show-toplevel)"
- [x] git switch main
- [x] git pull --ff-only
- [x] git fetch -p
- [x] git status -sb が clean
- [x] if dirty → STOP（stash/commit）

## 1) ブランチ作成
- [x] git switch -c s15-02-mkdirall-hardening-v1

## 2) 握りつぶし箇所の特定（探索for）
- [x] rg -n "MkdirAll\(" -S internal cmd docs | cat
- [x] if 0件 → skip（理由：対象なし）→ 以降中止
- [x] for each hit:
    - [x] 周辺10行確認（rg -n "MkdirAll\(" -n --context 5 ... 相当）
    - [x] if err 未処理 → fix候補としてメモ
    - [x] else continue

## 3) 修正（黙殺禁止）
- [x] for each fix候補:
    - [x] os.MkdirAll の戻り値を必ずチェック
    - [x] if err → return fmt.Errorf("mkdir ...: %w", err)
    - [x] error をログだけ出して継続はしない（監査ツールなので嘘になる）→ error STOP 方針

## 4) テスト追加（決定論）
- [x] *_test.go を追加 or 既存テストにケース追加
- [x] 失敗を作る手順：
    - [x] temp dir にファイル blocker を作る
    - [x] dir := blocker + "/child" に対して MkdirAll(dir) を呼ぶ
- [x] if エラーにならない → STOP（環境依存テスト禁止）
- [x] エラー文に “mkdir” と対象パスが含まれることを軽く確認

## 5) ローカルゲート
- [x] make ci-test
- [x] go test ./...
- [x] if FAIL → STOP

## 6) commit / push / PR
- [x] git diff --stat を確認（触ってる範囲が mkdir 周辺 + test だけ）
- [x] if 余計な変更 → STOP（除去）
- [x] git add -A
- [x] git commit -m "fix(reviewpack): fail fast on mkdir errors"
- [x] git push -u origin s15-02-mkdirall-hardening-v1
- [x] gh pr create --fill
