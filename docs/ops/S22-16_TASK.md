# S22-16 TASK — verify-il入口整合 + guardノイズ制御 + ship自動化

S22-16: 35% (WIP)

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
- [ ] （任意）`WITH_REVIEWPACK=1 SKIP_COMMIT=1 SKIP_PR=1 make s22-16-ship`

## 5. STATUS Sync
- [x] `docs/ops/STATUS.md` の S22-16 を 35% (WIP) へ更新
- [x] 進捗35%の根拠をこのTASKに記録（入口整合 + guardノイズ制御 + ship自動化）
