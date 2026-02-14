# S17-02 TASK — IL validator / canonicalizer (Contract v1)

## Step 0: Safety Snapshot（落ちない版）
- [x] `cd "$(git rev-parse --show-toplevel)"`
- [x] `git status -sb`
- [x] `git clean -ndx`（dry-run。削除はまだしない）
- [x] ブランチ確認: `git rev-parse --abbrev-ref HEAD`
- [x] main最新確認（必要なら）:
  - [x] `git fetch -p origin`
  - [x] `git log --oneline -n 3 --decorate`

## Step 1: 入口ファイルの機械的特定（迷子防止）
（S17-02 の勝負はここ。見つかるまで “推測で書かない”）
- [x] ROOT確定: `ROOT="$(git rev-parse --show-toplevel)"`
- [ ] IL参照探索（schema/contract/fixtures）:
  - [ ] `rg -n "il\.schema\.json|IL_CONTRACT_v1|docs/il|good_min\.json|bad_min\.json" "$ROOT/src" "$ROOT/tests" 2>/dev/null || true`
- [ ] normalize/pipeline探索:
  - [ ] `rg -n "normalize|jsonl|schema|contract|canonical|validator|il\b" "$ROOT/src" "$ROOT/src/satellite" "$ROOT/tests" 2>/dev/null || true`
- [ ] 見つかった “入口候補ファイル” を TASK に追記（パスを確定してから次へ）
  - [ ] IF 候補が複数 → 「呼び出し階層が一番上」(CLI/パイプ起点) を優先
  - [ ] IF 見つからない → STOP（rg結果を貼って設計側へ戻す）

## Step 2: 編集対象ファイルの作成（docs）
- [x] 作成:
  - [x] `"$ROOT/docs/ops/S17-02_PLAN.md"`
  - [x] `"$ROOT/docs/ops/S17-02_TASK.md"`（このファイル）
- [ ] docs を add してコミット（C0）
  - [ ] `git add "$ROOT/docs/ops/S17-02_PLAN.md" "$ROOT/docs/ops/S17-02_TASK.md"`
  - [ ] `git commit -m "docs(s17-02): add plan/task for IL validator+canonicalizer"`

## Step 3: validator 実装（Contract v1 準拠）
- [ ] Step1で確定した入口近傍に “validator責務” を追加（最小差分）
- [ ] schema 検証を実装（既存依存があるならそれを使う）
- [ ] Contract固有ルールを追加（例: forbidden_timestamp は FAIL）
- [ ] errors 形式を Contract に固定
  - [ ] FAIL時: errors は必ず非空
  - [ ] errors の順序を固定（ソート規則を実装）
- [ ] 単体テスト追加（fixtures根拠）
  - [ ] good_min → PASS
  - [ ] bad_min → FAIL（errors非空）
  - [ ] bad_forbidden_timestamp → FAIL（errors非空）

## Step 4: canonicalizer 実装（安定 JSON）
- [ ] validate を通った item のみ canonicalize（validate失敗は canonicalize しない）
- [ ] canonical JSON の規則を実装
  - [ ] sort keys
  - [ ] no extra spaces
  - [ ] JSONL は末尾 `\n`
- [ ] 決定論テスト
  - [ ] 同じ入力を2回 canonicalize して同一文字列
  - [ ] 期待するキー順/区切りが固定

## Step 5: normalize/pipeline 統合（導線は1本）
- [ ] 入口（もしくは出口1箇所）に validator → canonicalizer を組み込む
- [ ] “通らない経路” が残らないようにする（分岐があるならテストで塞ぐ）

## Step 6: Gate（いつもの儀式）
- [ ] `make test`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [ ] `git status -sb`（clean）

## Step 7: PR（1本で閉じる）
- [ ] `git push -u origin "$(git rev-parse --abbrev-ref HEAD)"`
- [ ] `gh pr create --fill`
- [ ] CI green 確認 → merge

## 進捗メモ（S17-02）
- C0 docs: 5%
- validator + tests: 40%
- canonicalizer + tests: 70%
- pipeline統合: 85%
- gates + PR merge: 100%
