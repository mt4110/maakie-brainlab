# S24-01-S24-10 THREAD v1 TASK — GitHub Actions/API Cost Optimization

Last Updated: 2026-02-26

## Progress

- S24-01-S24-10: 75% (S24-04/06/07/08 実装済み、closeout/evidence 固めを残し実装進行中)

## Ritual 22-16-22-99

- PLAN: `docs/ops/S24-01-S24-10-THREAD-V1_PLAN.md`
- DO: 下記チェックリスト順で最小差分実装
- CHECK: 軽量→中量→重量の順で段階検証
- SHIP: 小分けコミット + PR body に結果固定

## Checklist

### S24-01 Baseline

- [x] 直近 14 日の workflow 実行数/時間を観測し、baseline を PR body に記録
- [x] milestone workflows の API call 見積もりを記録
- [x] cost budget（lite/balanced/full）を PR body に記録

### S24-02 Trigger Minimization

- [x] `verify_pack.yml` に `paths` / `paths-ignore` を導入
- [x] docs-only 変更で heavy workflow が skip されることを確認
- [x] code-change で必要 workflow が起動することを確認

### S24-03 Concurrency Optimization

- [x] PR 系 workflow の concurrency group を統一
- [x] `cancel-in-progress` を PR デフォルトで有効化
- [x] main push 監査 run は cancel しないことを確認

### S24-04 Milestone API Slimming

- [x] `milestone_autofill` の重複 API fetch を削減
- [x] milestone 実変化時のみ dispatch する条件を導入
- [x] `milestone_required` が non-blocking 契約を維持することを確認

### S24-05 Artifact Budgeting

- [x] 成功時 artifact を要約中心に削減
- [x] 失敗時はデバッグ必要最小を upload
- [x] retention を用途別に短縮

### S24-06 Tiered Execution

- [x] `CI_COST_MODE` を導入（lite/balanced/full）
- [x] PR default を balanced に設定（品質優先）
- [x] manual/full 導線を残す

### S24-07 Schedule Throttling

- [x] `run_always_1h` の頻度を再設計（4h）
- [x] 手動 dispatch 導線を保持
- [x] 変更なし期間 skip 判定を追加（必要なら）

### S24-08 Required Checks Alignment

- [x] `ops/required_checks_sot.sh check` が通ることを確認
- [x] required checks 集合に milestone advisory 系が入っていないことを確認
- [x] drift 時の対応手順を PR body に記録

### S24-09 Rollout Safety

- [x] kill switch 変数を導入
- [x] phase 単位で revert 可能な差分に分割
- [x] rollback 手順を docs に記載

### S24-10 Closeout

- [x] Before/After 比較（run/minutes/artifacts/API calls）を PR body に固定
- [x] 未解決リスク・次スレ handoff を記載
- [x] closeout コミットを作成

## Validation Commands

軽量（毎PR）:

- [x] `bash ops/finalize_clean.sh --check`
- [x] `bash ops/required_checks_sot.sh check`
- [x] `python3 -m unittest -v tests/test_il_thread_runner_v2_doctor.py`
- [x] `python3 -m unittest -v tests/test_il_thread_runner_v2_suite.py`

中量（必要時）:

- [x] `make verify-il-thread-v2`

重量（closeout 前のみ）:

- [x] `make verify-il`
- [x] `source /path/to/your/nix/profile.d/nix-daemon.sh`
- [x] `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は `STATUS.md` ではなく PR body に記録する。
- 各フェーズで最低 1 行の `OK:/ERROR:/SKIP:` を残す。
- `SKIP` の場合は理由を 1 行で明記する。

## Commit Strategy

- 1 phase = 1 commit を基本とする（review と rollback を容易にする）。
- commit message 例:
  - `ci(s24-02): narrow verify_pack triggers by path filters`
  - `ci(s24-04): reduce milestone workflow api calls`
  - `ci(s24-07): throttle scheduled run_always frequency`

## Open Decisions

- [x] run_always の最終頻度（4h or 6h）
- [x] success artifact retention 日数（3d or 5d）
- [x] `milestone_required` status 投稿の最終扱い（job result 一本化するか）
