# S15-00 TASK — Fix pack_delta=2 by using PR-built reviewpack binary for baseline

禁止：set -euo pipefail（絶対禁止）
原則：失敗は握り潰さず、pack_delta=2 に落とす（嘘つかない）

## 0) Preflight（安全確認）

- MIGRATED: S21-MIG-S15-0001 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0002 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0003 (see docs/ops/S21_TASK.md)

## 1) 対象ファイル（実パス確定）

- MIGRATED: S21-MIG-S15-0004 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0005 (see docs/ops/S21_TASK.md)

## 2) 対象ブロック特定（探索 for / break / continue）

- MIGRATED: S21-MIG-S15-0006 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0007 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0008 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0009 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S15-0010 (see docs/ops/S21_TASK.md)

## 3) Init CI に 10_status.tsv truncate を追加（任意だが推奨）

- [x] $WF の - name: Init CI (Run Always) 内に以下を追加
- [x] : > .local/ci/10_status.tsv
- [x] if すでに存在 → skip（理由：既にtruncate済み）

## 4) Pack Delta Report の修正方針（根治）

目的：baseline(worktree=origin/main) で --skip-test が未定義でも壊れないようにする

- [x] Pack Delta Report step の run: | の先頭付近に以下を追加する場所を探す
- [x] if 追加位置が曖昧 → error STOP
- [x] PR workspace で reviewpack をビルドして temp に置く
- [x] REVIEWPACK_BIN="${{ runner.temp }}/reviewpack"
- [x] if ! go build -o "$REVIEWPACK_BIN" ./cmd/reviewpack; then
- [x] echo "[pack-delta] ERROR: go build reviewpack failed"
- [x] echo -e "pack_delta\t2" >> .local/ci/10_status.tsv
- [x] exit 0
- [x] end

## 5) baseline生成（go run 禁止 / PRバイナリで実行）

- [x] baseline生成箇所を置換
- [x] before: (cd "$BASE_DIR" && go run ./cmd/reviewpack/main.go submit ... --skip-test)
- [x] after : (cd "$BASE_DIR" && "$REVIEWPACK_BIN" submit --mode verify-only --skip-test)
- [x] if baseline生成コマンドが見つからない → error STOP

## 6) diff実行（PRバイナリで統一）

- [x] diff(json) を PRバイナリに置換
- [x] before: go run cmd/reviewpack/main.go diff ...
- [x] after : "$REVIEWPACK_BIN" diff ...
- [x] diff(text) も同様に置換（失敗しても warning でOK）
- [x] if text diff 失敗 → skip（理由：人間可読の補助、json側で判定する）

## 7) Exit code contract（pack_delta のみ特別扱い）

- [x] json diff の EC を取得（if/else で明示）
- [x] if diff 成功 → EC=0
- [x] else EC=$?
- [x] if EC==2 → pack_delta\t2
- [x] else → pack_delta\t0（差分=1は情報なので成功扱い）
- [x] ※将来 pack_delta\t1 を残す設計にするなら、Final Aggregation/CI Summary も揃えて変える（今は触らない）

## 8) worktree cleanup（破綻点を消す）

- [x] git worktree remove --force "$BASE_DIR" ... || true
- [x] git worktree prune

## 9) ローカル検証（最低ライン）

- [x] rg -n "runner.temp }}/reviewpack|go build -o" "$WF"
- [x] rg -n "go run .*reviewpack.*diff" "$WF" が Pack Delta Report 内で消えていること
- [x] if 残存 → error STOP（置換漏れ）
- [x] make ci-test（可能なら）
- [x] if FAIL → error STOP
- [x] go run cmd/reviewpack/main.go submit --mode verify-only（ローカルゲート）
- [x] if FAIL → error STOP

## 10) Commit / Push / PR

- [x] git diff --stat で変更が verify_pack.yml 中心であること確認
- [x] if 関係ないファイルが混ざる → STOP（混入を除去）
- [x] git add .github/workflows/verify_pack.yml
- [x] git commit -m "ci(s15): build reviewpack and use it for baseline pack-delta"
- [x] git push
- [x] CI で Final Aggregation が PASS になること（pack_delta=2 が消える）

## Future Steps (S15-07..10)
- [x] [S15_07_KICKOFF_TASK.md](S15_07_KICKOFF_TASK.md)
- [x] [S15_07_10_DEPENDENCY_MATRIX.md](S15_07_10_DEPENDENCY_MATRIX.md)
- [x] [S15_07_TASK.md](S15_07_TASK.md)
- [x] [S15_08_TASK.md](S15_08_TASK.md)
- [x] [S15_09_TASK.md](S15_09_TASK.md)
- [x] [S15_10_TASK.md](S15_10_TASK.md)
