# S19-02_TASK

## 実行ルール

*   set -e 禁止（明示的に error/STOP）
*   skip は理由を1行残す
*   error はその場で終了（嘘をつかない）

## Task

- [ ] [T0] Safety Snapshot <!-- id: T0 -->
    - [ ] git status -sb clean
    - [ ] ブランチ名確認（例 s19-02-prbodyfix-v1）

- [ ] [T1] 追加：pure ロジック <!-- id: T1 -->
    - [ ] internal/prbodyfix/normalize.go
    - [ ] sentinel行除去は TrimSpace 禁止（TrimLeft は可：indent吸収）
    - [ ] empty判定だけ TrimSpace
    - [ ] EnsureTrailingNewline は 1回だけ

- [ ] [T2] 追加：GitHub API クライアント <!-- id: T2 -->
    - [ ] token探索（GITHUB_TOKEN → GH_TOKEN → gh auth token）
    - [ ] GET PR / PATCH PR body
    - [ ] template取得（ref=baseSHA、失敗は空）

- [ ] [T3] 追加：cmd/prbodyfix/main.go <!-- id: T3 -->
    - [ ] CI event（GITHUB_EVENT_PATH）があればそれを優先
    - [ ] local mode は --pr 必須、repoは arg→git remote fallback
    - [ ] fork検出 → SKIP PASS
    - [ ] desired != current のときだけ PATCH（冪等）

- [ ] [T4] 置換：pr_body_required.yml <!-- id: T4 -->
    - [ ] JSブロック削除
    - [ ] actions/checkout
    - [ ] actions/setup-go
    - [ ] go run ./cmd/prbodyfix を実行
    - [ ] （保険）github-actions[bot] の edited は skip

- [ ] [T5] Unit Tests <!-- id: T5 -->
    - [ ] sentinel除去（prefix一致）
    - [ ] empty→template→minimal の順
    - [ ] newlineが二重にならない
    - [ ] 冪等（Normalize(Normalize(x)) == Normalize(x)）

- [ ] [T6] Gate <!-- id: T6 -->
    - [ ] go test ./... PASS
    - [ ] reviewpack submit --mode verify-only PASS

- [ ] [T7] 実証 <!-- id: T7 -->
    - [ ] 同じPRに対し2回連続実行 → 2回目は更新無し
    - [ ] sentinel混入 → 1回で除去 → 次回は更新無し
