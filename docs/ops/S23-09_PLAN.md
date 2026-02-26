# S23-09 PLAN — Thread Runner Artifact Doctor
Last Updated: 2026-02-26

## Goal
- thread runner の出力ディレクトリを自動監査し、summary/cases/artifacts の不整合を即検知する。

## Why Now
- S23-08 までで生成物は増えたため、手確認だと取りこぼしが出る。
- 後工程（S23-10 closeout）前に doctor を用意して、壊れた出力を早期に検出したい。

## Acceptance Criteria
- `scripts/il_thread_runner_v2_doctor.py` を追加し、`--run-dir` を検査できる。
- 最低検査項目:
  - `summary.json` と `cases.jsonl` の件数整合
  - `sha256_cases_jsonl` 一致
  - caseごとの compile artifact 存在
  - `entry_status=OK` ケースで `il.exec.report.json` 存在
- 異常時は `ERROR` ログを出し、最終 `status=ERROR` を返す。
- 正常系ユニットテストを追加する。

## Impacted Files
- `docs/ops/S23-09_PLAN.md` (new)
- `docs/ops/S23-09_TASK.md` (new)
- `scripts/il_thread_runner_v2_doctor.py` (new)
- `tests/test_il_thread_runner_v2_doctor.py` (new)

## Non-Goals
- 修復（auto-fix）機能
- 重量級データセット監査
