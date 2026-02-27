# S22-10 Blocker Fix (milestone_required) TASK
Last Updated: 2026-02-24

- [x] 0) repo確認（落ちない）
- [x] 1) OBS作成（OK: obs_dir=…）
- [x] 2) PR観測（#89/#90）
    - milestone 現状 / head branch / failing checks をログ
- [x] 3) milestone “S22-10” の 取得 or 作成
    - MID をログ（OK: milestone_number=…）
- [x] 4) PR #89 に milestone 付与 → 再観測
- [x] 5) PR #90 に milestone 付与 → 再観測
- [x] 6) milestone_required の再実行（必要時のみ）
    - rerun できなければ SKIP（理由1行）→ UI手動へ
- [x] 7) merge guard（#89 → #90 の順）
    - #89 dry-run → --merge
    - #90 dry-run → --merge（※#89 merge 後に）
- [x] 8) 追加：変更ファイルが200超なら Copilot review を挟む（best-effort）
    - changedFiles 観測して判断（重くない）
    - UIでCopilot review要求（できない/制限ならSKIP理由1行）
- [x] 9) マイルストーン close（best-effort / 失敗はSKIP）
