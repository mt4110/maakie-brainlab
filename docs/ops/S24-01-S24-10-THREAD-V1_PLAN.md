# S24-01-S24-10 THREAD v1 PLAN — GitHub Actions/API Cost Optimization

Last Updated: 2026-02-26

## Goal

- GitHub Actions の実行時間と GitHub API 呼び出しを削減しつつ、
  `required checks` の信頼性と運用再現性を維持する。
- S24-01 から S24-10 までを 1 本の thread として段階導入できる設計を固定する。

## Background

- 現状は `verify_pack` / `run_always_1h` / milestone workflows の起動頻度と処理密度が高く、
  実行コストと API コール数が増えやすい。
- 既存契約（S22-17）として、milestone 系は non-blocking 観測であり、
  merge の blocking 条件は required checks と check-runs に限定されている。
- そのため S24 では、blocking 契約を崩さず、
  「起動しない」「呼ばない」「アップロードしない」を徹底して総コストを下げる。

## Constraints (Non-negotiable)

- milestone 系は non-blocking のまま維持する。`milestone_required` を required checks 化しない。
- `docs/ops/STATUS.md` を進捗の source of truth にしない。進捗は PR 本文に書く。
- 重い処理は分割し、PR 通常運用は lightweight に寄せる。
- 失敗制御は stopless 契約（ログで判定、観測優先）を維持する。

## Non-Goals

- アプリ本体機能（`src/`, `internal/`）の仕様変更。
- eval アルゴリズムの精度改善。
- 既存 S23 thread runner v2 の振る舞い変更。

## Success Metrics (S24 Exit)

- PR 起因の Actions 総実行時間（分/週）を baseline 比で 40% 以上削減。
- milestone 系 workflow の API 呼び出し回数（calls/PR）を baseline 比で 50% 以上削減。
- `required checks` の false negative / false positive を増やさない（重大 incident 0）。
- `ops/pr_merge_guard.sh` の dry-run 成功率を維持（99%+ を目標）。

## Acceptance Criteria

- `S24-01..10` の設計が「phase ごとの目的・差分・検証・ロールバック」を持つ。
- workflow 側で以下の方針が実装可能な形で明文化される。
  - trigger 最小化（paths / event type / actor 条件）
  - concurrency 最適化（不要 run の cancel）
  - artifact 最小化（条件付き upload + retention 見直し）
  - milestone API 呼び出し削減（重複 fetch/post の削減）
- ローカル検証導線が先に定義され、Actions 連打を前提にしない。
- rollout は段階導入（canary → default）で、即時 rollback 手順を持つ。

## Impacted Files (Planned)

- `.github/workflows/ci.yml`
- `.github/workflows/verify_pack.yml`
- `.github/workflows/run_always_1h.yml`
- `.github/workflows/milestone_autofill.yml`
- `.github/workflows/milestone_required.yml`
- `.github/workflows/verify.yml`
- `ops/pr_merge_guard.sh`
- `ops/required_checks_sot.py`
- `ops/required_checks_sot.sh`
- `docs/ops/CI_REQUIRED_CHECKS.md`
- `docs/ops/PR_WORKFLOW.md`
- `docs/ops/S24-01-S24-10-THREAD-V1_PLAN.md`
- `docs/ops/S24-01-S24-10-THREAD-V1_TASK.md`
- `ops/ci/` (必要に応じて新規: コスト観測スクリプト)

## Architecture Summary

- Layer A: Trigger Cost Control
  - そもそも workflow を起動しない。
- Layer B: Run Cost Control
  - 起動後も job 条件分岐で重い手順を回避する。
- Layer C: API Cost Control
  - PR 情報取得・status 投稿・dispatch の重複を削る。
- Layer D: Artifact Cost Control
  - upload 対象・保持期間・タイミングを絞る。
- Layer E: Governance
  - required checks 契約を壊さず、milestone は advisory のまま運用。

## S24 Phase Design

### S24-01: Baseline Snapshot and Cost Budget Contract

目的:

- 変更前の run 分布と API call 密度を記録し、改善率を測る基準を作る。

設計:

- 過去 14 日の workflow 実行情報を収集（run count / duration / trigger type）。
- milestone workflows については 1 PR あたりの API call 見積もりを定義。
- `cost budget` を 3 区分で定義。
  - Lite: PR 通常運用
  - Balanced: release 直前
  - Full: 手動検証

受け入れ条件:

- baseline テーブルが docs に固定される。
- budget 超過判定ロジック（式）が docs に固定される。

ロールバック:

- なし（観測のみ）。

### S24-02: Trigger Minimization (paths + event filtering)

目的:

- docs-only / non-impact commit で heavy workflow を起動しない。

設計:

- `verify_pack.yml` に `paths` 条件を導入し、対象外差分で skip。
- `ci.yml` は lightweight lint を維持しつつ、PR イベント type を最小化。
- schedule/workflow_dispatch は維持し、push/pull_request の起動面積を縮小。

受け入れ条件:

- docs 更新のみの PR で heavy workflow が起動しない。
- コード変更 PR では必要 workflow が起動する。

リスク:

- paths 漏れで必要 run が skip される。

対策:

- allow-list を docs 化し、初期は conservative に広めに設定。

### S24-03: Concurrency and Cancellation Policy

目的:

- 同一 PR 上の古い run を早期に止め、重複課金を減らす。

設計:

- PR 起因 workflow は `cancel-in-progress: true` を標準化。
- `main` 向け push は cancel しない（監査証跡維持）。
- group key は `workflow + pr_number` を優先。

受け入れ条件:

- 同一 PR で連続 push した際、古い run が自動キャンセルされる。
- `main` の run 証跡は欠落しない。

### S24-04: Milestone Workflow API Slimming

目的:

- milestone 自動補完/判定での API 呼び出し重複を減らす。

設計:

- `milestone_autofill` と `milestone_required` の重複 `pulls.get` を削減。
- `workflow_dispatch` 連鎖を条件付き化。
  - milestone が変化した場合のみ dispatch。
- 手動 status POST 2本（required/advisory）の運用を見直し、
  workflow job 結果 + summary を基本に寄せる選択肢を用意。
- advisory は常に non-blocking を維持。

受け入れ条件:

- 1 PR あたりの milestone 系 API call が baseline 比で半減する。
- merge guard 契約（milestone non-blocking）が維持される。

### S24-05: Artifact Budgeting and Retention Compression

目的:

- upload 容量・保持日数・アップロード回数を削減する。

設計:

- artifact upload は `failure` 時優先、`success` は要約のみ。
- `retention-days` を用途別に短縮。
  - debug logs: 3-5 days
  - release evidence: 現行維持または明示 override
- `verify_pack` のアップロード対象を manifest 化し、不要ファイルを除外。

受け入れ条件:

- PR 成功時の artifact 容量が baseline 比で 60% 以上削減。
- 失敗時のデバッグに必要な最小証跡は欠落しない。

### S24-06: Run Tiering (Lite/Balanced/Full)

目的:

- 全 PR で同じ重さを実行しない。

設計:

- `vars.CI_COST_MODE`（または env）で tier を制御。
- Lite: lint + 最小 smoke
- Balanced: verify subset
- Full: 現行相当（手動 or 特定条件）
- PR デフォルトは Lite、`main` push で Balanced 以上を実行。

受け入れ条件:

- PR デフォルト実行時間が有意に短縮。
- リリース前に Full を実行できる導線が残る。

### S24-07: Schedule Throttling for run_always

目的:

- 時間課金を直接削減する。

設計:

- `run_always_1h` を 1h 固定から可変頻度へ移行。
  - 例: 4h 間隔をデフォルト
  - 手動 dispatch で即時実行可能
- 連続失敗時の再試行間隔を伸ばす（backoff）
- 変更なし期間は skip できる軽量判定を導入。

受け入れ条件:

- schedule 起因 run 回数が baseline 比で 50% 以上削減。
- 重大障害の検出遅延が許容範囲内（運用定義で明文化）。

### S24-08: Required Checks Contract Alignment (No Hidden Cost)

目的:

- required checks の過剰化を防ぎ、不要 workflow を required にしない。

設計:

- `ops/required_checks_sot.py` と docs SOT を同期し、
  必須チェック集合を最小必要に固定。
- milestone/check advisory 系は required に入れない。
- drift 検出は継続するが、観測コストが高い呼び出しは回数制限。

受け入れ条件:

- SOT と live required checks が一致。
- required checks 変更時にコスト影響が PR で可視化される。

### S24-09: Safe Rollout and Kill Switch

目的:

- コスト最適化の導入失敗時に即時復帰できるようにする。

設計:

- workflow 側に kill switch 変数（`CI_COST_MODE=full` など）を用意。
- phase 単位で enable/disable 可能な設計にする。
- rollback は docs に 1 コマンドで示す。

受け入れ条件:

- 異常時に 1 PR で旧挙動へ戻せる。
- rollback 実行時も required checks は通る。

### S24-10: Closeout, Evidence, and Handoff

目的:

- S24 thread を運用可能状態で閉じる。

設計:

- Before/After の比較表（run, minutes, artifacts, API calls）を固定。
- PR body に実行コマンド・結果・未解決リスクを記録。
- 次スレッド（S25）へ残課題を handoff。

受け入れ条件:

- closeout checklist が完了し、保守者が再現できる。
- no hidden gate（milestone blocking 追加など）がない。

## Stopless Pseudo-code (22-16-22-99 Compatible)

```text
STATE:
  STOP = 0
  MODE = CI_COST_MODE (lite|balanced|full)
  OBS = .local/obs/s24_cost_<UTC>

PLAN:
  if repo_root missing:
    print ERROR and set STOP=1
  else:
    collect baseline metrics and print OK

DO:
  for phase in [01..10]:
    if STOP == 1:
      print SKIP phase (reason: previous hard contract violation)
      continue

    try:
      apply minimal diff for phase
      print OK phase applied
    catch:
      print ERROR phase apply failed
      if phase in [08 required-check contract, 09 rollout safety]:
        STOP = 1
      else:
        continue

CHECK:
  run local lightweight checks first
  if checks fail:
    print ERROR and keep STOP as-is
  else:
    print OK

  run heavy checks only in full mode or explicit manual request
  if heavy skipped:
    print SKIP with one-line reason

SHIP:
  if STOP == 1:
    print SKIP ship (reason logged)
  else:
    commit by small batches
    prepare PR body with:
      - commands
      - result summary
      - cost delta
      - rollback note
```

## Rollout Plan

- Wave 1 (Canary):
  - S24-02,03,05 を限定導入（最も安全な削減）。
- Wave 2 (Policy):
  - S24-04,06,08 を導入し、API/required checks を最適化。
- Wave 3 (Schedule):
  - S24-07,09,10 を導入し、定常運用へ移行。

## Rollback Plan

- Trigger/Concurrency rollback:
  - workflow 条件差分のみ revert。
- Milestone API rollback:
  - `milestone_*` workflow を前版へ戻す。
- Schedule rollback:
  - cron を旧頻度（1h）に復帰。
- Required checks rollback:
  - `ops/required_checks_sot.sh write-sot` と docs SOT を再同期。

## Verification Strategy (Cost-aware)

軽量（毎PR）:

- `bash ops/finalize_clean.sh --check`
- `python3 -m unittest -v tests/test_il_thread_runner_v2_suite.py`
- `python3 -m unittest -v tests/test_il_thread_runner_v2_doctor.py`
- `bash ops/required_checks_sot.sh check`

中量（必要時）:

- `make verify-il-thread-v2`
- `bash ops/run_always_1h.sh` (manual only)

重量（closeout 時のみ）:

- `make verify-il`
- `ci-self up --ref "$(git branch --show-current)"`

## Risk Register

- R1: paths 条件漏れで必要 workflow が起動しない
  - Mitigation: canary で conservative 設定 + PR template に changed-path 表示
- R2: milestone workflow 省略で status の見え方が変わる
  - Mitigation: summary 出力を強化し、merge guard 観測ロジックを先に整備
- R3: schedule 間引きで障害検知遅延
  - Mitigation: 手動 dispatch と failure backoff で補完
- R4: required checks SOT drift
  - Mitigation: PR ごとに `required_checks_sot` をチェック

## Deliverables

- 本 PLAN
- TASK チェックリスト
- 実装 PR シリーズ（S24-01..10）
- closeout evidence（PR body に集約）
