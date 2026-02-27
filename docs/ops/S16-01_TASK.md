# S16-01（AI Contract “強制”）— repo実パス確定版 TASK

Taskは「実行順序の固定」が命。チェックボックスで“時系列の監査ログ”にする。

## 0. Safety Snapshot（必須）

- MIGRATED: S21-MIG-S16-01-0001 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S16-01-0002 (see docs/ops/S21_TASK.md)

## 1. 現状把握（探索 → break）

- MIGRATED: S21-MIG-S16-01-0003 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S16-01-0004 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S16-01-0005 (see docs/ops/S21_TASK.md)
  - 見つかったら PACK_VERSION期待値が埋まってるテスト/箇所をメモ（後で一括更新）

## 2. Contract v1 の実装（コードSOT化）

- MIGRATED: S21-MIG-S16-01-0006 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S16-01-0007 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S16-01-0008 (see docs/ops/S21_TASK.md)

### 2-A. PACK_VERSION のversioning
- MIGRATED: S21-MIG-S16-01-0009 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S16-01-0010 (see docs/ops/S21_TASK.md)

### 2-B. CONTRACT_v1 の生成（deterministic）
- [x] CONTRACT_v1 をJSONで生成（structで安定化、末尾\n付与）
- [x] 中身に contract_version:1 / pack_version / required_paths を含める

### 2-C. verify-onlyでの強制検証
- [x] CONTRACT_v1 の存在チェック（無ければFAIL）
- [x] logs/portable/rules-v1.json の存在 + JSON parse
- [x] logs/portable/*.log が最低1つ
- [x] 各 *.log に *.log.sha256 が存在（無ければFAIL）

## 3. テスト追加/更新（FAILが正しく出る）

- [x] PACK_VERSION=1 の互換テスト（契約強制しない）
- [x] PACK_VERSION=2 + CONTRACT_v1 欠落でFAIL
- [x] rules-v1.json が壊れてるJSONでFAIL
- [x] *.log あるのに *.log.sha256 が無い → FAIL
- [x] internal/reviewpack/diff_test.go の PACK_VERSION: "1\n" 期待値を更新（該当するなら）

## 4. Docs（SOT固定）

- [x] docs/ops/S16-01_PLAN.md を追加/更新（このTask/PlanをSOT化）
- [x] docs/ops/S16-01_TASK.md を追加/更新

## 5. Gate（最終）

- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'
- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'
- [x] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; git status -sb'

## 6. PR作成（1PRで閉じる）

- [x] 必要ファイルをadd → commit（複数コミット可、PRは分割しない）
- [x] push
- [x] PR作成（タイトル例：feat(reviewpack): enforce AI Contract v1 (PACK_VERSION v2)）
