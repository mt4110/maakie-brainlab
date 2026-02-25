# S22-16 PLAN — verify-il入口整合 + guardノイズ制御

## Goal
`make verify-il` を canonical IL 入口方針に揃え、verify-only運用で
「PASSだが ERROR ログ洪水」という監査ノイズを下げる。

## Scope (First Implementation)
1. `verify-il` から legacy forbidden (`scripts/il_check.py`) 呼び出しを除去
2. 代替として軽量スモーク (`scripts/il_entry_smoke.py`) を入口検証に使う
3. `ops/il_entrypoint_guard.py` の docs 由来ノイズを制御する
4. 反復手順（verify/commit/PR本文更新）をワンコマンド化する

## Deliverables (automation)
- `ops/s22_16_ship.py`
  - light gate 実行（guard + make verify-il）
  - commit（必要ファイルをstage、`.local` と review bundle tarball は除外）
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
