# S27-01-S27-10 THREAD v1 PLAN — Continuous Canary Ops and Readiness Automation

Last Updated: 2026-02-27

## Goal

- S26 で確立した `canary -> eval -> readiness -> closeout` を「単発実行」から「定常運用」へ昇格する。
- S27-10 Exit 時点で、`実接続 canary の継続監視 / medium eval taxonomy v2 / CI 定期 readiness / 長時間信頼性検証` が再現可能になる。

## Current Point (as of 2026-02-27)

- ブランチ: `ops/S27-01-S27-10`
- S26 closeout は `READY` 到達済みだが、provider env 未設定時の `SKIP` が未収束。
- S26 handoff で確定済みの着手項目は `S27-01..S27-03` の3件。

## Distance to Goal (Backward Estimate)

- S27-01 Provider Canary 定常運用化: 14%
- S27-02 Medium Eval Taxonomy v2: 14%
- S27-03 Release Readiness CI 定期実行: 12%
- S27-04 Incident Triage Pack: 10%
- S27-05 Policy Drift Guard: 10%
- S27-06 Reliability Soak (長時間): 10%
- S27-07 Acceptance Wall v2: 10%
- S27-08 Evidence Trend Index v2: 8%
- S27-09 SLO-based Go/No-Go: 6%
- S27-10 Closeout + S28 handoff: 6%

## Background

- S26 は thread 完走に成功したが、運用リスクは「継続観測」と「閾値運用」の不足に集約される。
- provider 実接続は env 依存で `SKIP` が発生し得るため、単回 PASS だけでは品質保証にならない。
- release readiness は手動実行中心のため、CI schedule での定常判定とトレンド監視が必要。

## Constraints (Non-negotiable)

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking のまま維持し、blocking gate を増やさない。
- `docs/ops/STATUS.md` を進捗 SOT にしない。進捗は TASK と PR body に固定する。
- ブランチ禁止パターン `codex/feat*` を使用しない。
- ship 前に `ci-self up --ref "$(git branch --show-current)"` を実行し、全 green を確認してから PR 更新する。
- stopless 運用（`OK:/WARN:/ERROR:/SKIP:`）を維持し、隠れ停止条件を入れない。

## Non-Goals

- 本スレッドで multi-region 本番冗長化を実装完了させること。
- 本スレッドでモデル精度最適化を限界まで追い込むこと。
- S25/S26 の設計資産を全面リライトすること。

## S27 Completion Definition (S27-10 Exit)

- provider canary の `SKIP率` と `reason_code 分布` が時系列で可視化され、閾値超過を検知できる。
- medium eval wall が運用データを含む taxonomy v2 に更新され、失敗分類の粒度が上がる。
- release readiness が CI 定期実行に接続され、`READY/BLOCKED` を継続監視できる。
- acceptance/reliability/evidence index が v2 仕様で接続され、phase 間の判定漏れがない。
- closeout artifact に Before/After・未解決リスク・S28 handoff が固定される。

## Success Metrics

- canary `SKIP率` を観測し、連続超過（例: 3 run 連続）を WARN で可視化できる。
- medium eval の failure taxonomy で `unknown` 割合を S26 比で削減する。
- CI schedule 起因の readiness 実行成功率を計測し、欠測 run を見逃さない。
- `go/no-go` 判定に必要な evidence 欠損を 0 件にする。

## Architecture Summary (S27 Planes)

### Plane-A: Signal Plane（観測）

- canary/eval/readiness の raw signal を phase ごとに evidence 化する。
- 時系列比較のため、latest + history 形式を保持する。

### Plane-B: Decision Plane（判定）

- taxonomy v2 と SLO 閾値に基づき、WARN/BLOCKED を一意に判定する。
- 判定根拠（閾値、分母、例外）を JSON に残す。

### Plane-C: Delivery Plane（運用）

- CI 定期実行とローカル手動実行を同一 I/F に揃える。
- rollback-only 導線を各 phase で維持する。

## Backward Phase Design (S27-10 -> S27-01)

### S27-10 Closeout + S28 Handoff

目的:
- S27 の運用成果を 1 artifact に集約し、S28 開始条件を固定する。

設計:
- Before/After（S26基準 vs S27定常運用）を固定。
- unresolved risk を「継続観測が必要な項目」に限定して列挙。
- S28-01..03 の初期着手候補を handoff として確定。

受け入れ条件:
- `docs/evidence/s27-10/closeout_latest.{json,md}` が生成される。
- PR body に closeout block を貼れる最小要約が出る。

### S27-09 SLO-based Go/No-Go

目的:
- readiness 判定を単純 PASS/FAIL から、SLO 閾値付き go/no-go に昇格する。

設計:
- canary skip率、eval failure比率、acceptance pass率を合成判定する。
- `HARD_BLOCK` と `SOFT_WARN` を分離し、non-blocking 契約と整合させる。

受け入れ条件:
- `READY/BLOCKED` に加え `WARN_ONLY` を出力可能。
- 判定理由を gate ごとに JSON 明記できる。

### S27-08 Evidence Trend Index v2

目的:
- 単発 latest だけでなく、run trend で劣化を検出する。

設計:
- S27-01..07 evidence の履歴 index を生成。
- missing/failed/warn の件数推移を markdown table で出力。

受け入れ条件:
- index v2 で phase 欠損を即判定できる。
- 直近 N run の比較が 1 artifact で読める。

### S27-07 Acceptance Wall v2

目的:
- S26 acceptance を運用前提へ拡張し、再現不能 failure を減らす。

設計:
- case に severity と expected fallback を追加。
- provider/env 未設定時の期待挙動を case 化し、SKIP を意図的に評価する。

受け入れ条件:
- case schema v2 が固定される。
- severity 別の pass/fail 集計が evidence に出る。

### S27-06 Reliability Soak (Long-run)

目的:
- 短時間 smoke では出ない retry/backoff 劣化を検出する。

設計:
- 長時間 run の soak モードを追加（軽量代理データで可）。
- reason_code の時間帯偏りと連続失敗数を集計する。

受け入れ条件:
- soak summary artifact が生成される。
- 連続失敗検知ルール（閾値）が docs で固定される。

### S27-05 Policy Drift Guard

目的:
- provider/eval/readiness の契約 drift を自動検知する。

設計:
- TOML/JSON schema hash を比較し、差分を drift report 化。
- 破壊的変更を WARN/ERROR で分類する。

受け入れ条件:
- drift report が phase 実行時に必ず残る。
- hash と変更要約が同時に保存される。

### S27-04 Incident Triage Pack

目的:
- 障害発生時に「次に何を見るか」を固定し MTTR を短縮する。

設計:
- canary/eval/readiness の最小診断情報を 1 つの triage pack に集約。
- top reason_code、最近の失敗 run、推奨 rollback command を提示する。

受け入れ条件:
- triage artifact 単体で初動判断できる。
- rollback-only command が常に表示される。

### S27-03 Release Readiness to CI Schedule

目的:
- release-readiness を手動中心から CI 定期監視へ昇格する。

設計:
- schedule workflow から readiness runner を定期起動。
- failed/warn の通知用 summary を生成（non-blocking）。

受け入れ条件:
- schedule run で readiness artifact が更新される。
- manual 実行と同じ出力 schema を維持する。

### S27-02 Medium Eval Wall v2

目的:
- 運用データを取り込んだ taxonomy v2 で failure 分類精度を上げる。

設計:
- S26 medium dataset を拡張し、運用起因ケースを追加。
- taxonomy を `provider/network/schema/timeout/unknown` へ再編。

受け入れ条件:
- dataset meta と taxonomy v2 が docs で固定される。
- unknown 比率と主要 failure 比率が evidence に出る。

### S27-01 Provider Canary Operations

目的:
- provider 実接続 canary を定常運用モードに移行し、SKIP率を継続監視する。

設計:
- canary policy に `skip_rate_warn_threshold` と `window_size` を追加。
- run 履歴を保持し、単発 PASS で過信しない観測を行う。

受け入れ条件:
- SKIP率 trend artifact を出力できる。
- env 未設定時でも WARN と次アクションが固定表示される。

## Planned Impacted Files

- `docs/ops/S27-01-S27-10-THREAD-V1_PLAN.md`
- `docs/ops/S27-01-S27-10-THREAD-V1_TASK.md`
- `docs/ops/S27-01_PROVIDER_CANARY_OPS.toml` (new)
- `docs/ops/S27-02_MEDIUM_EVAL_WALL_V2.toml` (new)
- `docs/ops/S27-07_ACCEPTANCE_CASES_V2.json` (new)
- `docs/ops/S27-10_CLOSEOUT.md` (new)
- `scripts/ops/s27_provider_canary_ops.py` (new)
- `scripts/ops/s27_medium_eval_wall_v2.py` (new)
- `scripts/ops/s27_release_readiness_schedule.py` (new)
- `scripts/ops/s27_incident_triage_pack.py` (new)
- `scripts/ops/s27_policy_drift_guard.py` (new)
- `scripts/ops/s27_reliability_soak.py` (new)
- `scripts/ops/s27_acceptance_wall_v2.py` (new)
- `scripts/ops/s27_evidence_trend_index.py` (new)
- `scripts/ops/s27_slo_readiness.py` (new)
- `scripts/ops/s27_closeout.py` (new)
- `tests/test_s27_provider_canary_ops.py` (new)
- `tests/test_s27_medium_eval_wall_v2.py` (new)
- `tests/test_s27_release_readiness_schedule.py` (new)
- `tests/test_s27_incident_triage_pack.py` (new)
- `tests/test_s27_policy_drift_guard.py` (new)
- `tests/test_s27_reliability_soak.py` (new)
- `tests/test_s27_acceptance_wall_v2.py` (new)
- `tests/test_s27_evidence_trend_index.py` (new)
- `tests/test_s27_slo_readiness.py` (new)
- `tests/test_s27_closeout.py` (new)
- `.github/workflows/run_always_1h.yml` (schedule integration)
- `Makefile` (new targets)
- `docs/ops/ROADMAP.md`
- `docs/evidence/s27-01/*` ... `docs/evidence/s27-10/*`

## Validation Strategy

軽量:
- `make ops-now`
- `python3 -m unittest -v tests/test_s27_provider_canary_ops.py`
- `python3 -m unittest -v tests/test_s27_medium_eval_wall_v2.py`
- `python3 -m unittest -v tests/test_s27_release_readiness_schedule.py`
- `python3 -m unittest -v tests/test_s27_policy_drift_guard.py`

中量:
- `make s27-provider-canary-ops`
- `make s27-medium-eval-wall-v2`
- `make s27-release-readiness-schedule`
- `make s27-reliability-soak`
- `make s27-slo-readiness`
- `make s27-closeout`

重量（ship前）:
- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Risks and Mitigations

- リスク: provider env 未設定のまま運用され、SKIP が常態化する。
- 対策: SKIP率閾値と連続超過検知を固定し、SLO 判定に反映する。

- リスク: taxonomy v2 で分類は増えたが unknown が実質温存される。
- 対策: unknown を fail-open にせず、triage pack で優先調査対象に昇格する。

- リスク: CI schedule 実行失敗が unnoticed で劣化を見逃す。
- 対策: schedule run 欠測を evidence index v2 で missing として可視化する。

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  freeze S27-10 completion and backward phases
DO:
  implement S27-01..S27-10 in small stopless runners
CHECK:
  run lightweight -> medium -> heavyweight gates in order
SHIP:
  commit by phase, then record command/result facts in PR body
```
