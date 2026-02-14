# S15-00 TASK — Fix pack_delta=2 by using PR-built reviewpack binary for baseline

禁止：set -euo pipefail（絶対禁止）
原則：失敗は握り潰さず、pack_delta=2 に落とす（嘘つかない）

## 0) Preflight（安全確認）

- [ ] cd "$(git rev-parse --show-toplevel)"
- [ ] git status -sb を確認
- [ ] if working tree dirty → STOP（stash/commit してから）

## 1) 対象ファイル（実パス確定）

- [ ] WF=".github/workflows/verify_pack.yml" を固定
- [ ] if test -f "$WF" が false → error STOP（パス違い）

## 2) 対象ブロック特定（探索 for / break / continue）

- [ ] for pat in ["- name: Pack Delta Report", "main-worktree", "pack_delta"]:
- [ ] rg -n "$pat" "$WF" -n
- [ ] if hit → break
- [ ] else continue
- [ ] if 最後まで hit 0 → error STOP（別workflow/別stepの可能性、勝手に決めない）

## 3) Init CI に 10_status.tsv truncate を追加（任意だが推奨）

- [ ] $WF の - name: Init CI (Run Always) 内に以下を追加
- [ ] : > .local/ci/10_status.tsv
- [ ] if すでに存在 → skip（理由：既にtruncate済み）

## 4) Pack Delta Report の修正方針（根治）

目的：baseline(worktree=origin/main) で --skip-test が未定義でも壊れないようにする

- [ ] Pack Delta Report step の run: | の先頭付近に以下を追加する場所を探す
- [ ] if 追加位置が曖昧 → error STOP
- [ ] PR workspace で reviewpack をビルドして temp に置く
- [ ] REVIEWPACK_BIN="${{ runner.temp }}/reviewpack"
- [ ] if ! go build -o "$REVIEWPACK_BIN" ./cmd/reviewpack; then
- [ ] echo "[pack-delta] ERROR: go build reviewpack failed"
- [ ] echo -e "pack_delta\t2" >> .local/ci/10_status.tsv
- [ ] exit 0
- [ ] end

## 5) baseline生成（go run 禁止 / PRバイナリで実行）

- [ ] baseline生成箇所を置換
- [ ] before: (cd "$BASE_DIR" && go run ./cmd/reviewpack/main.go submit ... --skip-test)
- [ ] after : (cd "$BASE_DIR" && "$REVIEWPACK_BIN" submit --mode verify-only --skip-test)
- [ ] if baseline生成コマンドが見つからない → error STOP

## 6) diff実行（PRバイナリで統一）

- [ ] diff(json) を PRバイナリに置換
- [ ] before: go run cmd/reviewpack/main.go diff ...
- [ ] after : "$REVIEWPACK_BIN" diff ...
- [ ] diff(text) も同様に置換（失敗しても warning でOK）
- [ ] if text diff 失敗 → skip（理由：人間可読の補助、json側で判定する）

## 7) Exit code contract（pack_delta のみ特別扱い）

- [ ] json diff の EC を取得（if/else で明示）
- [ ] if diff 成功 → EC=0
- [ ] else EC=$?
- [ ] if EC==2 → pack_delta\t2
- [ ] else → pack_delta\t0（差分=1は情報なので成功扱い）
- [ ] ※将来 pack_delta\t1 を残す設計にするなら、Final Aggregation/CI Summary も揃えて変える（今は触らない）

## 8) worktree cleanup（破綻点を消す）

- [ ] git worktree remove --force "$BASE_DIR" ... || true
- [ ] git worktree prune

## 9) ローカル検証（最低ライン）

- [ ] rg -n "runner.temp }}/reviewpack|go build -o" "$WF"
- [ ] rg -n "go run .*reviewpack.*diff" "$WF" が Pack Delta Report 内で消えていること
- [ ] if 残存 → error STOP（置換漏れ）
- [ ] make ci-test（可能なら）
- [ ] if FAIL → error STOP
- [ ] go run cmd/reviewpack/main.go submit --mode verify-only（ローカルゲート）
- [ ] if FAIL → error STOP

## 10) Commit / Push / PR

- [ ] git diff --stat で変更が verify_pack.yml 中心であること確認
- [ ] if 関係ないファイルが混ざる → STOP（混入を除去）
- [ ] git add .github/workflows/verify_pack.yml
- [ ] git commit -m "ci(s15): build reviewpack and use it for baseline pack-delta"
- [ ] git push
- [ ] CI で Final Aggregation が PASS になること（pack_delta=2 が消える）

## Future Steps (S15-07..10)
- [ ] [S15_07_KICKOFF_TASK.md](S15_07_KICKOFF_TASK.md)
- [ ] [S15_07_10_DEPENDENCY_MATRIX.md](S15_07_10_DEPENDENCY_MATRIX.md)
- [ ] [S15_07_TASK.md](S15_07_TASK.md)
- [ ] [S15_08_TASK.md](S15_08_TASK.md)
- [ ] [S15_09_TASK.md](S15_09_TASK.md)
- [ ] [S15_10_TASK.md](S15_10_TASK.md)
