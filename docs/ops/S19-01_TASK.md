# S19-01_TASK

## 実行ルール

*   set -e 禁止（止まらない）
*   失敗時は error: を1行出して STOP
*   skip は理由を1行残す（監査ログ）

## Task

- MIGRATED: S21-MIG-S19-01-0001 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0002 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0003 (see docs/ops/S21_TASK.md)

- MIGRATED: S21-MIG-S19-01-0004 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0005 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0006 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0007 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0008 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0009 (see docs/ops/S21_TASK.md)
    - MIGRATED: S21-MIG-S19-01-0010 (see docs/ops/S21_TASK.md)

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
