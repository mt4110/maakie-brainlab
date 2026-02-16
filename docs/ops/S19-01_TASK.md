# S19-01_TASK

## 実行ルール

*   set -e 禁止（止まらない）
*   失敗時は error: を1行出して STOP
*   skip は理由を1行残す（監査ログ）

## Task

- [ ] [T0] Safety Snapshot（状況固定） <!-- id: T0 -->
    - [ ] git status -sb が clean である
    - [ ] ブランチが s19-01-prkit-v1 である

- [ ] [T1] 修正：cmd/prkit/main.go を “--fill依存” から脱却 <!-- id: T1 -->
    - [ ] dirty なら STOP（git status --porcelain）
    - [ ] diff commits=0 なら STOP（upstream..HEAD）
    - [ ] title = 最新コミット件名
    - [ ] body = template読み込み → sentinel(prefix)除去 → evidence 注入 → 最小保証
    - [ ] gh pr create --title/--body-file を実行
    - [ ] PR既存なら “作らず PASS” にする

- [ ] [T2] 修正：ops/pr_create.sh を止まらない＋--base が通る形に <!-- id: T2 -->
    - [ ] set -e を削除
    - [ ] BASE を引数 or env で受けられる
    - [ ] go run cmd/prkit/main.go --base "$BASE" create 形式にする

- [ ] [T3] 修正：pr_body_required.yml を “テンプレ取れなくてもPASS” に <!-- id: T3 -->
    - [ ] fork PR は notice + PASS
    - [ ] sentinel(prefix)除去（startsWith）
    - [ ] empty → template取得できれば採用
    - [ ] template空/取得失敗 → 最小本文（HeadSHA + Run URL）を注入して PASS
    - [ ] 変化が無いなら update しない（冪等）

- [ ] [T4] docs/ops を追加（設計を repo に固定） <!-- id: T4 -->
    - [ ] docs/ops/S19-01_PLAN.md
    - [ ] docs/ops/S19-01_TASK.md

- [ ] [T5] テスト <!-- id: T5 -->
    - [ ] go test ./... PASS
    - [ ] reviewpack submit --mode verify-only PASS（bundle更新）

- [ ] [T6] 実証（運用破綻しないことの証拠） <!-- id: T6 -->
    - [ ] ./ops/pr_create.sh で PR 作成が詰まらない
    - [ ] PR本文に evidence が自動で入る（ローカル主砲）
    - [ ] sentinel を手で混入→ CI が除去して PASS（保険）
    - [ ] STOPテスト：diff commits=0 で prkit create が STOP（正しい失敗）
