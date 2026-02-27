# S28-01-S28-10 THREAD v5 PLAN — Slow-Paced One-Pass Delivery

Last Updated: 2026-02-27

## Goal

- S28-01..S28-10 を一気通貫で維持しつつ、実行速度を意図的に落として設計品質を先に固定する。
- CI上限を守るため、`ci-self` 実行を ship 直前の最小回数に集約する。
- ゴール逆算（S28-10 -> S28-01）で、実装の手戻りと再実行を減らす。

## Current Point (2026-02-27)

- Branch: `ops/S28-01-S28-10`
- v4 では機能面の実装・テスト・一気通貫実行は完了済み。
- 課題は「進行速度」と「CI実行頻度」であり、v5 では実装テンポ制御を主対象とする。

## Non-negotiables

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、blocking gate を増やさない。
- `docs/ops/STATUS.md` を進捗 SOT に使わない（TASK + PR body に固定）。
- PR作成/更新前に `ci-self up --ref "$(git branch --show-current)"` を実行し、green確認後に進める。
- 禁止ブランチ `codex/feat*` を使わない。

## v5 Cadence Contract

- 追加フェーズ: `Phase-1 Design Freeze` を新設し、設計固定に目安60分を確保する。
- 実装は `Phase-2` でまとめて行い、途中でCIを回さない。
- `ci-self` は ship 直前に1回を原則とし、失敗時の再実行は修正後1回まで（合計最大2回）に制限する。

## Completion Definition (v5 Exit)

- S28-10 までの成果物契約が PLAN/TASK で再固定され、次アクションが明確である。
- 実装変更が必要な場合は、S28関連スクリプトを1バッチで更新しローカル検証を完了している。
- `make verify-il` と `ci-self` の最終ゲートが green である。
- PR body に実行コマンドと結果（OK/WARN/ERROR/SKIP）が固定されている。

## Backward Design (S28-10 -> S28-01)

### S28-10 Closeout
- closeout の最終判定と S29 handoff の整合を最終確認する。

### S28-09 SLO Readiness v2
- READY/WARN_ONLY/BLOCKED を再判定し、hard/softの根拠を維持する。

### S28-08 Evidence Trend Index v3
- S28-01..07 の履歴連結と欠損検知を確認する。

### S28-07 Acceptance Wall v3
- 受入条件を severity付きで評価し、残リスクを可視化する。

### S28-06 Reliability Soak v2
- streak と recovery signal を合成し、運用劣化の見逃しを防ぐ。

### S28-05 Policy Drift Guard v2
- S28 contract file の drift を継続検知する。

### S28-04 Incident Triage Pack v2
- recovery/taxonomy/notify を triage packet として統合する。

### S28-03 Readiness Notify
- readiness 判定を通知payload化し、送信結果の可視化を維持する。

### S28-02 Taxonomy Feedback Loop
- unknown case 候補と収集アクション生成を維持する。

### S28-01 Provider Canary Recovery
- non-pass streak と recovery方針を固定し、自動復旧根拠を保持する。

## Delivery Phases (v5)

1. Phase-1 Design Freeze (new / 60m target)
   - ゴール逆算、変更範囲、CI budget、exit条件を先に固定。
2. Phase-2 Implementation Batch
   - 必要なコード変更をまとめて反映（分割実装しない）。
3. Phase-3 Local Check Batch
   - ユニットテスト + `make ops-now` + 必要な中量コマンドをローカルで一括実行。
4. Phase-4 End-to-End Verification
   - S28-01..S28-10 を一気通貫で1回実行し、artifact整合を確認。
5. Phase-5 Ship Gate
   - `make verify-il` -> `ci-self up --ref ...` を順に1回ずつ実行。

## Planned Impacted Files

- `docs/ops/S28-01-S28-10-THREAD-V5_PLAN.md`
- `docs/ops/S28-01-S28-10-THREAD-V5_TASK.md`
- `docs/ops/ROADMAP.md`
- （必要時のみ）`scripts/ops/s28_*.py`, `tests/test_s28_*.py`

## Validation Strategy (CI Budgeted)

ローカル（Phase-3/4）:
- `make ops-now`
- `python3 -m unittest -v tests/test_s28_slo_readiness_v2.py`
- `python3 -m unittest -v tests/test_s28_closeout.py`
- `make s28-slo-readiness-v2`
- `make s28-closeout`

ship直前（Phase-5）:
- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## Stopless Pseudo-code (22-16-22-99)

```text
PLAN:
  freeze design, scope, and CI budget before coding
DO:
  implement required changes in one cohesive batch
CHECK:
  run local checks and one end-to-end pass without CI spam
SHIP:
  run verify-il and ci-self once, then update PR body
```
