# S22-16 PLAN — verify-il入口整合 + guardノイズ制御

## Goal
`make verify-il` を canonical IL 入口方針に揃え、verify-only運用で
「PASSだが ERROR ログ洪水」という監査ノイズを下げる。

## Scope (First Implementation)
1. `verify-il` から legacy forbidden (`scripts/il_check.py`) 呼び出しを除去
2. 代替として軽量スモーク (`scripts/il_entry_smoke.py`) を入口検証に使う
3. `ops/il_entrypoint_guard.py` の docs 由来ノイズを制御する
4. 反復手順（verify/commit/PR本文更新）をワンコマンド化する
5. PR同期の直前に `ci-self` all-green gate を必須化する
6. `branch-name-guard` / `milestone_required` を観測して closeout 条件に含める

## Deliverables (automation)
- `ops/s22_16_ship.py`
  - light gate 実行（guard + make verify-il）
  - commit（必要ファイルをstage、`.local` と review bundle tarball は除外）
  - PR同期前に `ci-self up --ref <branch>` を実行し、all-green以外は停止
  - `gh pr checks` watch出力（最終スナップショット）を解釈できる all-green 判定
  - PR本文生成（guard summary / make verify-il 要約を自動反映）
  - `gh` が使える場合は PR create/edit まで実行
  - `--with-reviewpack` 指定時のみ verify-only を1回実行して本文へ追記
- `make s22-16-ship`
  - デフォルト: commit + PR同期（reviewpack は実行しない）
  - 例: `WITH_REVIEWPACK=1 make s22-16-ship`
  - 例: `SKIP_COMMIT=1 SKIP_PR=1 make s22-16-ship`（観測のみ）

## Edited Files (absolute paths)
- `/Users/takemuramasaki/dev/maakie-brainlab/Makefile`
- `/Users/takemuramasaki/dev/maakie-brainlab/scripts/il_entry_smoke.py`
- `/Users/takemuramasaki/dev/maakie-brainlab/ops/il_entrypoint_guard.py`
- `/Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S22-16_PLAN.md`
- `/Users/takemuramasaki/dev/maakie-brainlab/docs/ops/S22-16_TASK.md`
- `/Users/takemuramasaki/dev/maakie-brainlab/docs/ops/STATUS.md`
- `/Users/takemuramasaki/dev/maakie-brainlab/ops/s22_16_ship.py`

## Stop Condition (do not proceed)
- `make verify-il` に `scripts/il_check.py` が残る場合
- `ops/il_entrypoint_guard.py` が runtime 対象（Makefile/ops/.github）以外で
  `::error::` を大量出力する場合
- `scripts/il_entry_smoke.py` が
  `OK: phase=end STOP=0/1` の期待観測を検証できない場合
- 自動化ヘルパーが PR本文に `guard_summary` / `make verify-il` 要約を埋められない場合
- `ci-self` が all-green でないまま PR 作成/更新へ進む場合

## Policy Decision (this thread)
- `milestone_required` 失敗への対応は **A** を採用:
  - PR #102 に `S22-16` milestone を設定して green 化する。
  - milestone 系 workflow/判定の除外（B）はこのスレでは実施しない。
