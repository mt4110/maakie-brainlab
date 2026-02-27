# S18-02 TASK
Hardening — new_ops_phase.sh truthful write + PHASE_ID sanitize

## Scope Lock (v1 / frozen)
- ops/new_ops_phase.sh のみ最小修正（生成物フォーマットは互換維持）
- Truthful write:
  - tmp write 失敗時に OK を出さない（ERROR: 1行 + 非0終了）
  - mv 失敗時に OK を出さない（ERROR: 1行 + 非0終了）
  - 失敗時は可能なら tmp を削除（ゴミ抑制）
- PHASE_ID sanitize (v1):
  - / を含む → ERROR
  - .. を含む → ERROR
  - 先頭が . → ERROR
  - ※正規表現ガチ縛りや追加ルールは次フェーズ扱い

## Non-goals
- 新フラグ追加（dry-run等）しない
- canonical pin 更新しない（Observationのみ）
- 生成物フォーマットをいじりすぎない（互換維持）

## Steps (fixed order)
- [x] 0) Safety snapshot: git status / branch確認
- [x] 1) docs/ops/S18_PLAN.md に S18-02 行があること（無ければ追記）
- [x] 2) ops/new_ops_phase.sh: truthful write + PHASE_ID sanitize を実装（最小パッチ）
- [x] 3) Smoke:
  - [x] NG: ../X / A/B / .. / .S18-00 が必ず拒否される（ERROR: 1行 + 非0）
  - [x] OK: S18-98 等は生成できる（生成後に削除）
  - [x] 事故ファイルが残ってないこと（docs, docs/ops を確認）
- [x] 4) Gates:
  - [x] make test
  - [x] go run cmd/reviewpack/main.go submit --mode verify-only
- [x] 5) Commit / Push / PR update:
  - [x] git add -A
  - [x] git commit
  - [x] git push（PR #54 に反映される）

## Progress update rules (S18-02)
- docs scope lock完了：20%
- script修正＋smoke：70%
- gates PASS：90%
- merge：100%
