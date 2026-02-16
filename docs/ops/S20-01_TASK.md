# S20-01 Task — RAG tuning readiness v1

## Progress
- 0% Start
- 10% Plan/Task fixed (commit済みで世界線固定)
- 25% Spec placeholders added (rag/ の3ファイル作成)
- 40% Eval spec fixed (dataset + run output + failure taxonomy)
- 70% Determinism spec fixed (chunk/index config + record format)
- 85% Injection policy fixed (policy + detection log format)
- 90% Gates pass
- 100% PR merged

## C0: Safety Snapshot
- [ ] `git status -sb` clean
- [ ] `git grep -n "file URL（fileスキーム）\|ユーザHOME絶対パス" -- docs/ops || true`

## C1: Create reserved spec paths (薄くてOK、でも作る)
- [ ] `mkdir -p docs/ops/rag`
- [ ] `docs/ops/rag/EVAL_SPEC_v1.md` を作る（空にしない：目的と“固定するもの”だけ書く）
- [ ] `docs/ops/rag/DETERMINISM_SPEC_v1.md` を作る（同上）
- [ ] `docs/ops/rag/INJECTION_POLICY_v1.md` を作る（同上）

## C2: Eval Wall (measurable tuning)
- [ ] 評価セットの置き場所・フォーマット・最低限の失敗分類を EVAL_SPEC に固定
- [ ] 実行出力（ログ/結果）の保存先・命名規則を EVAL_SPEC に固定
- [ ] “良くなった/悪くなった” を判定する最小メトリクスを EVAL_SPEC に定義（比較は前回runとの差分）

## C3: Determinism Moat (repeatable index/retrieval)
- [ ] chunk・正規化・順序の仕様を DETERMINISM_SPEC に固定（仕様名をつける）
- [ ] index作成の設定（モデル/embedding/チャンク設定/入力スナップショット）を「記録項目」として固定

## C4: Injection Gate (baseline guard)
- [ ] 検索結果中の命令を命令として扱わない方針を INJECTION_POLICY に固定
- [ ] 最低限の検知（危険フレーズ等）と「検知ログのフォーマット」を固定（検知でOK）

## C5: ROADMAP update
- [ ] `docs/ops/ROADMAP.md` の S20 セクションに S20-01 を追記

## C6: Gates
- [ ] `go test ./...`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`

## C7: PR
- [ ] `git push -u origin HEAD`
- [ ] PR作成（`./ops/pr_create.sh` or `gh pr create --fill`）
- [ ] CI green → merge
