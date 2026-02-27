# S26-01-S26-10 THREAD v1 PLAN — Precision AI Orchestration Core to Closeout

Last Updated: 2026-02-27

## Goal

- AIオーケストレーションの心臓部を、`失敗しても止まらない` 前提で精密化する。
- S26-10 Exit 時点で、`provider canary -> eval wall -> rollback -> orchestration -> safety -> acceptance -> reliability -> readiness -> closeout` の一周を再現可能にする。

## Current Point (as of 2026-02-27)

- ブランチ: `ops/S26-05-S26-06`
- S26-01..S26-04 の実装/evidence は完了済み。
- S26-05..S26-10 は本スレッドで拡張実装する。

## Distance to Goal (Backward Estimate)

- S26-05 Regression Safety: 12%
- S26-06 Acceptance Wall: 14%
- S26-07 Reliability Report: 12%
- S26-08 Evidence Index: 10%
- S26-09 Release Readiness: 16%
- S26-10 Closeout: 16%
- 既存 S26-01..S26-04 整合確認: 20%

## Background

- S25 で ML/RAG/LangChain の最小一周は完了したが、外部 provider 実接続の失敗モードは引き続き変動する。
- S26-01..04 でコア runner は成立したため、次は thread 完走に必要な gate と closeout を固定する。
- 「今どこか」「何が ship 判定か」を evidence 1本で追える形にする必要がある。

## Constraints (Non-negotiable)

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking のまま維持する（blocking gate を増やさない）。
- `STATUS.md` を進捗 SOT にしない。進捗は TASK と PR body に固定する。
- stopless 運用（`OK:/WARN:/ERROR:/SKIP:`）を維持し、隠れ停止条件を入れない。

## Non-Goals

- 本スレッドで本番SaaS向け multi-region 可用性を完成させること。
- 本スレッドでモデル品質最適化を限界までやり切ること。
- 既存 S25 資産を全面リライトすること。

## Orchestration Design (Target Skeleton)

### Plane-A: Policy Plane（決める）

- Provider policy contract を TOML で固定:
  - `timeout_sec`, `max_retries`, `retry_backoff_ms`, `jitter_ms`
  - `retryable_reason_codes`, `non_retryable_reason_codes`
  - `circuit_open_sec`, `max_inflight`
- Policy hash を evidence に出し、実行結果と必ず紐づける。

### Plane-B: Execution Plane（動かす）

- S26-01..04: canary/eval/rollback/core を順序実行。
- S26-05..09: safety/acceptance/reliability/index/readiness を段階追加。
- S26-10: closeout artifact で thread を閉じる。

### Plane-C: Evidence Plane（証明する）

- 各 phase は `docs/evidence/s26-0x/*` に JSON + Markdown を保存。
- S26-08 で phase evidence を index 化。
- S26-09 で ship 判定を固定し、S26-10 で unresolved risk/handoff を固定。

## Backward Phase Design (S26-10 -> S26-01)

### S26-10 Closeout

- Before/After（品質・速度・運用負荷）を closeout artifact に固定。
- unresolved risk と S27 handoff を明記する。

### S26-09 Release Readiness

- S26-01..08 を gate 化し、`READY/BLOCKED` を単一判定で出す。
- rollback command を同時に提示する。

### S26-08 Evidence Index

- S26 phase artifact を 1 つの index に集約する。
- missing/failed/warn を一覧化し、判定漏れを防ぐ。

### S26-07 Reliability Report

- provider canary の pass/fail/skip と reason_code 分布を集計する。
- 実接続ケースが 0 件でも WARN として可視化する（隠れ失敗にしない）。

### S26-06 Acceptance Wall

- S26-01..05 の主要契約を JSON assertion で固定する。
- acceptance failure taxonomy を evidence 化する。

### S26-05 Regression Safety

- S26 core tests を lightweight 実行し、壊してはいけない契約を確認する。
- non-blocking marker の docs 契約を確認する。

### S26-04 Orchestration Core

- S26-01..03 を順序実行し、stopless で統合結果を保存する。

### S26-03 Rollback Artifact

- rollback command 実行ログを artifact として常時収集する。

### S26-02 Medium Eval Wall

- medium dataset 契約と分布を固定し、再現可能な評価壁を維持する。

### S26-01 Provider Canary

- provider 実接続 smoke と timeout/retry policy を契約化する。

## S26 Completion Definition (S26-10 Exit)

- `make ops-now` が S26 TASK を参照し、進捗と次アクションを即時表示する。
- S26-01..S26-07 の各 artifact が最新化される。
- S26-08 evidence index で missing/failed を即判定できる。
- S26-09 release readiness が `READY/BLOCKED` を一意に返す。
- S26-10 closeout で Before/After・unresolved risk・handoff が固定される。

## Planned Impacted Files

- `docs/ops/S26-01-S26-02-THREAD-V1_PLAN.md`
- `docs/ops/S26-01-S26-02-THREAD-V1_TASK.md`
- `docs/ops/S26-06_ACCEPTANCE_CASES.json` (new)
- `docs/ops/S26-10_CLOSEOUT.md` (new)
- `scripts/ops/s26_regression_safety.py` (new)
- `scripts/ops/s26_acceptance_wall.py` (new)
- `scripts/ops/s26_reliability_report.py` (new)
- `scripts/ops/s26_evidence_index.py` (new)
- `scripts/ops/s26_release_readiness.py` (new)
- `scripts/ops/s26_closeout.py` (new)
- `tests/test_s26_regression_safety.py` (new)
- `tests/test_s26_acceptance_wall.py` (new)
- `tests/test_s26_reliability_report.py` (new)
- `tests/test_s26_evidence_index.py` (new)
- `tests/test_s26_release_readiness.py` (new)
- `tests/test_s26_closeout.py` (new)
- `Makefile` (new targets)
- `docs/ops/ROADMAP.md`
- `docs/evidence/s26-05/*`
- `docs/evidence/s26-06/*`
- `docs/evidence/s26-07/*`
- `docs/evidence/s26-08/*`
- `docs/evidence/s26-09/*`
- `docs/evidence/s26-10/*`

## Validation Strategy

- 軽量:
  - `make ops-now`
  - `python3 -m unittest -v tests/test_s26_provider_canary.py`
  - `python3 -m unittest -v tests/test_s26_medium_eval_wall.py`
  - `python3 -m unittest -v tests/test_s26_rollback_artifact.py`
  - `python3 -m unittest -v tests/test_s26_orchestration_core.py`
  - `python3 -m unittest -v tests/test_s26_regression_safety.py`
  - `python3 -m unittest -v tests/test_s26_acceptance_wall.py`
  - `python3 -m unittest -v tests/test_s26_reliability_report.py`
  - `python3 -m unittest -v tests/test_s26_evidence_index.py`
  - `python3 -m unittest -v tests/test_s26_release_readiness.py`
  - `python3 -m unittest -v tests/test_s26_closeout.py`
- 中量:
  - `make s26-regression-safety`
  - `make s26-acceptance-wall`
  - `make s26-reliability-report`
  - `make s26-evidence-index`
  - `make s26-release-readiness`
  - `make s26-closeout`
- 重量（ship前）:
  - `make verify-il`
  - `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
  - `ci-self up --ref "$(git branch --show-current)"`

## Risks and Mitigations

- リスク: provider env 未設定時に canary が SKIP となる。
- 対策: reliability report で WARN を必ず出し、closeout で unresolved risk 化する。

- リスク: thread後半で evidence 参照漏れが起きる。
- 対策: evidence index と release readiness で missing を gate 化する。

- リスク: closeout 時に判断材料が PR body に散る。
- 対策: closeout artifact に Before/After と handoff を固定する。

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  freeze S26-10 completion and backward phases
DO:
  implement S26-05..S26-10 runners + tests + evidence
CHECK:
  run lightweight -> medium -> heavyweight in order
SHIP:
  commit small, update PR body with command/result facts
```
