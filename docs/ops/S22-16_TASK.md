# S22-16 TASK — verify-il入口整合 + guardノイズ制御 + ship自動化

S22-16: 95% (WIP)

## 0. Kickoff / Scope Fix
- [x] Confirm branch is S22-16 work branch
- [x] Confirm theme: verify-il entrypoint alignment + guard noise control
- [x] Update S22-16 PLAN/TASK with concrete scope and stop condition

## 1. Implementation (stopless / low CPU)
- [x] `Makefile` verify-il から `scripts/il_check.py` を除去
- [x] verify-il に `scripts/il_entry_smoke.py` を組み込み
- [x] `scripts/il_entry_smoke.py` を修正し、期待観測を
  `OK: phase=end STOP=0` / `OK: phase=end STOP=1` に一致させる
- [x] `ops/il_entrypoint_guard.py` を修正
- [x] ERROR対象を `Makefile` / `ops` / `.github` に限定
- [x] `docs/ops` は検索対象外化（歴史的記述ノイズ回避）
- [x] guard summary を1行で出力（`errors/warns/canonical`）

## 2. Validation (light only)
- [x] `python3 ops/il_entrypoint_guard.py`
- [x] `make verify-il`

## 3. Mechanical Flow Automation (human-unaware)
- [x] `ops/s22_16_ship.py` を追加
- [x] `make s22-16-ship` を追加
- [x] ship helper が guard と verify-il の要約を PR本文へ自動埋め込み
- [x] ship helper が commit / PR create-edit を stopless で実行
- [x] reviewpack verify-only は `--with-reviewpack` 指定時のみ1回実行

## 4. Validation (automation dry-run)
- [x] `SKIP_COMMIT=1 SKIP_PR=1 make s22-16-ship`
- [x] （任意）`WITH_REVIEWPACK=1 SKIP_COMMIT=1 SKIP_PR=1 make s22-16-ship`
  - 観測: `go` 未導入環境では reviewpack verify-only は `WARN`（他フローは STOP=0）

## 5. STATUS Sync
- [x] `docs/ops/STATUS.md` の S22-16 を最新進捗へ同期
- [x] 進捗は PR 本文をソースオブトゥルースとし、`STATUS.md` はミラー運用

## 6. CI Gate / Policy Sync
- [x] ship helper に `ci-self all-green` gate を実装（green 以外は PR 作成/更新停止）
- [x] `ci-self` の `gh pr checks` 出力形式でも all-green 判定できるよう補強
- [x] `branch-name-guard` をチェック観測項目に反映
- [x] `milestone_required` FAILURE の方針を A で固定（milestone を設定して green 化）
- [x] PR #102 に `S22-16` milestone を設定し、`milestone_required` が SUCCESS になること
- [ ] `mergeStateStatus=BEHIND` 解消（必要時 main 取り込み）後に再チェック

## 7. Closeout
- [ ] 全チェック green + 方針反映を確認後、S22-16 を 100% に更新
