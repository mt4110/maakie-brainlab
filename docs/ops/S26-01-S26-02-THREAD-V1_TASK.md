# S26-01-S26-10 THREAD v1 TASK — Precision AI Orchestration Core to Closeout

Last Updated: 2026-02-27

## Progress

- S26-01-S26-10: 98% (S26-01..10 実装/evidence 完了、ship前最終 gate のみ残し)

## Ritual 22-16-22-99

- PLAN: `docs/ops/S26-01-S26-02-THREAD-V1_PLAN.md`
- DO: 下記チェックリストを上から最小差分で実装
- CHECK: 軽量 -> 中量 -> 重量の順で検証
- SHIP: 小分けコミット + PR body に結果固定

## Current-Point Rule (SOT)

- 現在地は `branch + TASK progress + checklist未完了先頭` の3点で定義する。
- 進捗 SOT は本 TASK と PR body（`STATUS.md` には依存しない）。
- 毎作業開始時に `make ops-now` を実行し、同じ形式で確認する。

## Checklist

### S26-00 Kickoff

- [x] S26-01/S26-02 の PLAN/TASK を作成
- [x] backward design（残距離と到達条件）を固定
- [x] PR body テンプレート（S26用）を固定

### S26-01 Provider Canary + Timeout/Retry Policy

- [x] provider policy TOML（timeout/retry/backoff/circuit）を定義
- [x] `scripts/ops/s26_provider_canary.py` を追加
- [x] provider 実接続 smoke を stopless 形式で実装
- [x] reason_code taxonomy（retryable / non-retryable）を固定
- [x] rollback-only 実行導線を 1 コマンドで保証
- [x] evidence（JSON/MD）を `docs/evidence/s26-01/` に保存
- [x] unit tests を追加（timeout / retry / circuit-open）

### S26-02 Medium Eval Wall (RAG/ML/LangChain Shared)

- [x] medium dataset v1 を新設（ID/version 固定）
- [x] dataset meta（目的/制約/ケース分布）を追加
- [x] `scripts/ops/s26_medium_eval_wall.py` を追加
- [x] RAG/ML/LangChain 共通集計（pass_rate/latency/reason_code）を実装
- [x] mini vs medium の delta 表示を追加
- [x] evidence（JSON/MD）を `docs/evidence/s26-02/` に保存
- [x] unit tests を追加（dataset/schema/summary）

### S26-03 Rollback Artifact

- [x] `scripts/ops/s26_rollback_artifact.py` を追加
- [x] rollback command 実行ログの artifact 化を実装
- [x] evidence（JSON/MD）を `docs/evidence/s26-03/` に保存
- [x] unit tests を追加（helper レベル）

### S26-04 Orchestration Core

- [x] `scripts/ops/s26_orchestration_core.py` を追加
- [x] S26-01..03 の順序実行と stopless 集約を実装
- [x] evidence（JSON/MD）を `docs/evidence/s26-04/` に保存
- [x] unit tests を追加（helper レベル）

### S26-05 Regression Safety

- [x] `scripts/ops/s26_regression_safety.py` を追加
- [x] non-blocking 契約チェックを実装
- [x] evidence（JSON/MD）を `docs/evidence/s26-05/` に保存
- [x] unit tests を追加

### S26-06 Acceptance Wall

- [x] acceptance cases（JSON）を追加
- [x] `scripts/ops/s26_acceptance_wall.py` を追加
- [x] evidence（JSON/MD）を `docs/evidence/s26-06/` に保存
- [x] unit tests を追加

### S26-07 Reliability Report

- [x] `scripts/ops/s26_reliability_report.py` を追加
- [x] canary reason_code 分布/成功率を集計
- [x] evidence（JSON/MD）を `docs/evidence/s26-07/` に保存
- [x] unit tests を追加

### S26-08 Evidence Index

- [x] `scripts/ops/s26_evidence_index.py` を追加
- [x] S26-01..07 の artifact index を生成
- [x] evidence（JSON/MD）を `docs/evidence/s26-08/` に保存
- [x] unit tests を追加

### S26-09 Release Readiness

- [x] `scripts/ops/s26_release_readiness.py` を追加
- [x] S26-01..08 の gate 判定（READY/BLOCKED）を固定
- [x] evidence（JSON/MD）を `docs/evidence/s26-09/` に保存
- [x] unit tests を追加

### S26-10 Closeout

- [x] closeout note を `docs/ops/S26-10_CLOSEOUT.md` に追加
- [x] `scripts/ops/s26_closeout.py` を追加
- [x] Before/After + unresolved risk + handoff を artifact 化
- [x] evidence（JSON/MD）を `docs/evidence/s26-10/` に保存
- [x] unit tests を追加

## Validation Commands

軽量（毎PR）:

- [x] `make ops-now`
- [x] `python3 -m unittest -v tests/test_s26_provider_canary.py`
- [x] `python3 -m unittest -v tests/test_s26_medium_eval_wall.py`
- [x] `python3 -m unittest -v tests/test_s26_rollback_artifact.py`
- [x] `python3 -m unittest -v tests/test_s26_orchestration_core.py`
- [x] `python3 -m unittest -v tests/test_s26_regression_safety.py`
- [x] `python3 -m unittest -v tests/test_s26_acceptance_wall.py`
- [x] `python3 -m unittest -v tests/test_s26_reliability_report.py`
- [x] `python3 -m unittest -v tests/test_s26_evidence_index.py`
- [x] `python3 -m unittest -v tests/test_s26_release_readiness.py`
- [x] `python3 -m unittest -v tests/test_s26_closeout.py`

中量（必要時）:

- [x] `make s26-provider-canary`
- [x] `make s26-medium-eval-wall`
- [x] `make s26-rollback-artifact`
- [x] `make s26-orchestration-core`
- [x] `make s26-regression-safety`
- [x] `make s26-acceptance-wall`
- [x] `make s26-reliability-report`
- [x] `make s26-evidence-index`
- [x] `make s26-release-readiness`
- [x] `make s26-closeout`

重量（ship前）:

- [x] `make verify-il`
- [x] `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- [x] `ci-self up --ref "$(git branch --show-current)"`

## Evidence Policy

- 進捗・判断・コマンド結果は PR body に固定する。
- 各 phase で最低1行の `OK:/WARN:/ERROR:/SKIP:` を残す。
- `SKIP` は理由を1行で明示する。
