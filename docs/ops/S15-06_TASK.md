# S15-06: AI Work v2 (record/replay) — Task

## Rules
- **for** は探索にのみ使用（見つけたら break）
- **skip** は理由を必ず1行
- **error** はその場で終了（嘘を付かない）
- **fail-fast** は ( … ) サブシェルで閉じる

## 1. 編集対象パス確定 [DONE]
- [x] S15-05関連コミットの痕跡を見る
- [x] “AI lane 実装の中核” を探索
- [x] 確定した実ファイルパスを PLAN に貼る

## 2. ドキュメント作成 [DONE]
- [x] Plan 作成 (`docs/ops/S15-06_PLAN.md`)
- [x] Task 作成 (`docs/ops/S15-06_TASK.md`)
- [x] Acceptance 作成 (`docs/ops/S15-06_ACCEPTANCE.md`)

## 3. 実装：record/replay/verify-only [DONE]
- [x] WorkSpec の canonicalize + spec_hash 算出を実装
- [x] Store (`.local/aiwork/<hash>/`) を実装
- [x] Providers 実装 (mock provider)
- [x] Verifier 実装 (Spec一致, verify-only gate)

## 4. Make/CI 接続 [DONE]
- [x] `make ai-smoke` を更新（mockでPASS）
- [x] `make ai-verify` を更新（replay + verify-onlyでPASS）
- [x] CI に組み込み (mockで回ることを確認)

## 5. Evidence [DONE]
- [x] `docs/evidence/s15-06/` に記録
- [x] 要点のみを保存（秘密混入なし）

## 6. 最終ゲート [DONE]
- [x] `make test` PASS
- [x] `make ai-smoke` PASS
- [x] `make ai-verify` PASS
- [x] `git status` clean
