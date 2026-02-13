# S15-03 TASK: Diagnostics & Test Hygiene

## Target branch
- s15-03-diagnostics-test-hygiene

## Files to touch (expected)
- internal/reviewpack/fs.go
- internal/reviewpack/repo.go
- internal/reviewpack/pack.go
- internal/reviewpack/utils.go
- internal/reviewpack/artifacts.go
- internal/reviewpack/evidence.go
- internal/reviewpack/mkdir_test.go (or add new *_test.go)
- docs/ops/S15_03_PLAN.md
- docs/ops/S15_03_TASK.md

---

## 0) Preflight (no heavy)
- [ ] cd "$(git rev-parse --show-toplevel)"
- [ ] git status -sb
- [ ] rg -n "log\.Fatalf|_ = os\.WriteFile\(|os\.WriteFile\(" internal/reviewpack/*.go internal/reviewpack/*_test.go
- [ ] make test (baseline PASS を保存)

IF make test fails:
- [ ] STOP: failure log を貼り、原因箇所を最短で特定してから次へ

---

## 1) Diagnostics: log.Fatalf に “失敗した dir/path” を含める
FOR each log.Fatalf site:
- [ ] if message に target が無い:
  - [ ] update to include path/dir (and keep existing msgFatal* style)
  - [ ] prefer changing msgFatal* constants + call sites (一貫性優先)
- [ ] else:
  - [ ] SKIP（変更不要）として残す

重点チェック（例）:
- [ ] fs.go: MkdirAll/MkdirTemp 系の fatal が path を持っているか
- [ ] repo.go: chdir failure が “どこへ chdir したかったか” を出しているか

---

## 2) Test hygiene: product code の `_ = os.WriteFile(` を消す
- [ ] rg -n "_ = os\.WriteFile\(" internal/reviewpack
- [ ] for each match:
  - [ ] replace with `if err := os.WriteFile(...); err != nil { log.Fatalf(... target path ..., err) }`
  - [ ] message は既存 msgFatalWrite / msgFatalCreate 等の流儀に揃える（存在するならそれを使う）

NOTE:
- tests 側の os.WriteFile は「必ず err チェック」になっているかも確認
- Copilot 指摘が既に解決済みなら、grep と該当箇所で “already clean” を証拠化して終わらせる

---

## 3) mkdir fail-fast の “reviewpack 側検証” をテストで担保
目的:
- OS の挙動ではなく、reviewpack が fail-fast することを検証する

- [ ] 現状の mkdir_test.go が何を見ているか読む
- [ ] if reviewpack の fail-fast を直接検証できていない:
  - [ ] subprocess/helper パターンのテストを追加（同一 test バイナリを子プロセス起動）
  - [ ] 子プロセス側で “ディレクトリ作成が必ず失敗する状況” を作る
    - 例: `blocker` を regular file として作り、その下に logs/raw を作らせる導線を踏む
  - [ ] 親プロセスで exit code と stderr を検証（メッセージに target dir が含まれることも検証）
- [ ] else:
  - [ ] 既存テストが reviewpack の fail-fast を見ていることを説明できる形にコメントを追加

---

## 4) Docs整合
- [ ] docs/ops/S15_03_PLAN.md を追加/更新（このタスクと一致）
- [ ] docs/ops/S15_03_TASK.md を追加/更新
- [ ] if S15-02 docs とメッセージ形式や仕様が矛盾:
  - [ ] docs を S15-03 実装に合わせて調整

---

## 5) Evidence & PR
- [ ] rg evidence を貼れる形で保存:
  - [ ] rg -n "_ = os\.WriteFile\(" internal/reviewpack (ゼロ確認)
  - [ ] rg -n "log\.Fatalf" internal/reviewpack (対象箇所把握)
- [ ] make test のログを PR evidence にする
- [ ] git diff --stat
- [ ] commit (small, reviewable)
- [ ] git push -u origin s15-03-diagnostics-test-hygiene
- [ ] gh pr create --fill (or templateに合わせる)
