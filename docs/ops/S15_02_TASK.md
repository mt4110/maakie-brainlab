# S15-02 TASK — Fail fast on MkdirAll errors

禁止：set -euo pipefail（絶対禁止）

## 0) Preflight
- [ ] cd "$(git rev-parse --show-toplevel)"
- [ ] git switch main
- [ ] git pull --ff-only
- [ ] git fetch -p
- [ ] git status -sb が clean
- [ ] if dirty → STOP（stash/commit）

## 1) ブランチ作成
- [ ] git switch -c s15-02-mkdirall-hardening-v1

## 2) 握りつぶし箇所の特定（探索for）
- [ ] rg -n "MkdirAll\(" -S internal cmd docs | cat
- [ ] if 0件 → skip（理由：対象なし）→ 以降中止
- [ ] for each hit:
    - [ ] 周辺10行確認（rg -n "MkdirAll\(" -n --context 5 ... 相当）
    - [ ] if err 未処理 → fix候補としてメモ
    - [ ] else continue

## 3) 修正（黙殺禁止）
- [ ] for each fix候補:
    - [ ] os.MkdirAll の戻り値を必ずチェック
    - [ ] if err → return fmt.Errorf("mkdir ...: %w", err)
    - [ ] error をログだけ出して継続はしない（監査ツールなので嘘になる）→ error STOP 方針

## 4) テスト追加（決定論）
- [ ] *_test.go を追加 or 既存テストにケース追加
- [ ] 失敗を作る手順：
    - [ ] temp dir にファイル blocker を作る
    - [ ] dir := blocker + "/child" に対して MkdirAll(dir) を呼ぶ
- [ ] if エラーにならない → STOP（環境依存テスト禁止）
- [ ] エラー文に “mkdir” と対象パスが含まれることを軽く確認

## 5) ローカルゲート
- [ ] make ci-test
- [ ] go test ./...
- [ ] if FAIL → STOP

## 6) commit / push / PR
- [ ] git diff --stat を確認（触ってる範囲が mkdir 周辺 + test だけ）
- [ ] if 余計な変更 → STOP（除去）
- [ ] git add -A
- [ ] git commit -m "fix(reviewpack): fail fast on mkdir errors"
- [ ] git push -u origin s15-02-mkdirall-hardening-v1
- [ ] gh pr create --fill
