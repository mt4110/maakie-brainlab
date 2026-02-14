# S16-01（AI Contract “強制”）— repo実パス確定版 TASK

Taskは「実行順序の固定」が命。チェックボックスで“時系列の監査ログ”にする。

## 0. Safety Snapshot（必須）

- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; git status -sb'
- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; test "$(git rev-parse --abbrev-ref HEAD)" != "main"'

## 1. 現状把握（探索 → break）

- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; rg -n "PACK_VERSION|logs/portable|rules-v1\\.json|CONTRACT_v1" internal/reviewpack | sed -n "1,120p"'
- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; rg -n "PACK_VERSION" internal/reviewpack/artifacts.go internal/reviewpack/verify.go internal/reviewpack/submit.go'
- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; rg -n "\"1\\\\n\"|PACK_VERSION.*1" internal/reviewpack | sed -n "1,120p"'
  - 見つかったら PACK_VERSION期待値が埋まってるテスト/箇所をメモ（後で一括更新）

## 2. Contract v1 の実装（コードSOT化）

- [ ] （提案）契約定義を1箇所に集約（例：internal/reviewpack/contract_v1.go を作る or verify.go に節として置く）
- [ ] PACK_VERSION >= 2 のとき、pack root に CONTRACT_v1 を 必ず生成
- [ ] verify-only は PACK_VERSION を読み、>=2 のとき Contract v1 を強制検証する

### 2-A. PACK_VERSION のversioning
- [ ] PACK_VERSION の現行値が "1\n" なら、今回から "2\n" を生成するよう更新
- [ ] 互換性：verify側は 1 も検証できるように残す

### 2-B. CONTRACT_v1 の生成（deterministic）
- [ ] CONTRACT_v1 をJSONで生成（structで安定化、末尾\n付与）
- [ ] 中身に contract_version:1 / pack_version / required_paths を含める

### 2-C. verify-onlyでの強制検証
- [ ] CONTRACT_v1 の存在チェック（無ければFAIL）
- [ ] logs/portable/rules-v1.json の存在 + JSON parse
- [ ] logs/portable/*.log が最低1つ
- [ ] 各 *.log に *.log.sha256 が存在（無ければFAIL）

## 3. テスト追加/更新（FAILが正しく出る）

- [ ] PACK_VERSION=1 の互換テスト（契約強制しない）
- [ ] PACK_VERSION=2 + CONTRACT_v1 欠落でFAIL
- [ ] rules-v1.json が壊れてるJSONでFAIL
- [ ] *.log あるのに *.log.sha256 が無い → FAIL
- [ ] internal/reviewpack/diff_test.go の PACK_VERSION: "1\n" 期待値を更新（該当するなら）

## 4. Docs（SOT固定）

- [ ] docs/ops/S16-01_PLAN.md を追加/更新（このTask/PlanをSOT化）
- [ ] docs/ops/S16-01_TASK.md を追加/更新

## 5. Gate（最終）

- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'
- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'
- [ ] bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; git status -sb'

## 6. PR作成（1PRで閉じる）

- [ ] 必要ファイルをadd → commit（複数コミット可、PRは分割しない）
- [ ] push
- [ ] PR作成（タイトル例：feat(reviewpack): enforce AI Contract v1 (PACK_VERSION v2)）
