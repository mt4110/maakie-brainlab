# S21-01 PLAN — Outer Wall Triage v1

## Goal
運用の衛生を外壁として固定する：
STATUS + Triage儀式 + 単一SOT原則 + 進捗観測（スナップショット）

## Inputs (Observed Reality)
- docs/ops の checkbox 状況（done/todo/total）
- backlogホットスポット（ファイル別件数）
- 上位ファイル（例: S8_TASK / S18-00_TASK / S15_TASK ...）

## Plan (Pseudo-code; No-Exit)
- if repo root が取れない:
    - error: "ERROR: not in git repo"
    - STOP（ここで人間が止まる）
- else:
    - continue

- if docs/ops/S21_*.md が無い:
    - create（4ファイル）
- else:
    - skip: "already exists"

- if docs/ops/STATUS.md が無い:
    - create（外壁）
- else:
    - update（S21行を追加）

- try:
    - Snapshot を採取（done/todo/total/percent と hot list）
  catch:
    - print "ERROR: snapshot failed"
    - STOP

- for hot_file in Top-N:
    - for todo_line in first K:
        - choose one:
            - MIGRATE → S21_TASK Backlog へ移植
            - PARK → STATUSへ理由付きで積む
            - GRAVEYARD → STATUSへ理由付きで埋葬
        - 古い場所は checkbox 行を残さない（参照行に置換して漂流を止める）
        - continue

## Acceptance
- STATUS が単一入口として機能する
- S21の運用ルールが docs/ops だけで再現できる
- 進捗スナップショットが S21-01_TASK に残っている
- “古いbacklog項目の漂流” を減らす第一歩（少なくとも上位1ファイルで移植が走っている）
