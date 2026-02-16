# S18-02 Hardening — new_ops_phase.sh truthful write + PHASE_ID sanitize

## Goal
S18-01で作った `ops/new_ops_phase.sh` を、v1の範囲で「嘘をつかない」「事故らない」道具に仕上げる。
- 失敗を成功と言わない（truthful write）
- PHASE_ID 由来の事故（パス逸脱/隠しファイル化）をv1で最小ブロックする（sanitize）

## Scope Lock (ONLY)
This phase changes ONLY the following paths:
- `ops/new_ops_phase.sh` (truthfulness + PHASE_ID sanitize)
- `docs/ops/S18-02_PLAN.md`
- `docs/ops/S18-02_TASK.md`
- `docs/ops/S18_PLAN.md` (S18-02 行の追加＝開始許可)
- `docs/ops/S18_TASK.md` (必要なら追記)

Behavior changes (v1 minimal):
1) Truthful write
- `mv` 失敗時に `OK:` を出さない
- 失敗時は `ERROR:` を1行出して非0終了
- tmpファイルは可能なら削除（ゴミ抑制）
- tmpへの出力が空/不成立っぽい場合（`-s`判定）も `ERROR:` で非0終了

2) PHASE_ID sanitize (v1 minimal)
- `/` を含む → `ERROR:` + exit non-zero
- `..` を含む → `ERROR:` + exit non-zero
- 先頭が `.` → `ERROR:` + exit non-zero
(正規表現ガチ縛りや追加ルールは次フェーズ扱い)

## Non-goals
- 新フラグ追加（dry-run等）しない
- canonical pin 更新しない（Observationのみ）
- 生成物フォーマットをいじりすぎない（互換維持）

## Acceptance (Definition of Done)
- NG入力が必ず拒否される（`ERROR:` 1行 + 非0 / `OK:` は出ない）
  - `../X` / `A/B` / `..` / `.S18-00` が拒否される
- 書き込み失敗時に `OK:` が出ない
- tmpが残りにくい（失敗時は可能なら削除）
- Gates:
  - `make test` PASS
  - `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

## Progress update rules (S18-02)
- docs scope lock完了：20%
- script修正＋smoke：70%
- gates PASS：90%
- merge：100%
