# S32-01-S32-30 THREAD v1 PLAN — IL Scale, Quality, and Daily Usability

Last Updated: 2026-02-28

## Goal

- S31 で開通した `compile -> entry -> thread runner` を「fixture中心」から「実データ寄り運用」へ引き上げる。
- IL の不足機能（実データ収集、分類、可観測性、SLO、運用自動化）を追加し、使い勝手をさらに改善する。
- S32-30 Exit 時点で、開発者と運用者が同じ evidence から同じ判断を再現できる状態にする。

## Current Point (2026-02-28)

- Branch: `ops/S32-01-S32-30`
- 直前スレッド: `S31-01..S31-30` 完了（closeout/handoff = PASS）
- S31 からの引き継ぎ優先ギャップ:
  - RAG bridge が fixture 中心で、non-fixture corpus 運用が弱い。
  - compile の品質ぶれ（provider/model/profile 選択）が運用者依存になりやすい。
  - 長時間・分散 run の運用可視化（dashboard/SLO/分類）をさらに強化できる。

## Non-negotiables

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、milestone-required gate は追加しない。
- `docs/ops/STATUS.md` を進捗 SOT に使わない（TASK + PR body に固定）。
- PR作成/更新前に `ci-self` gate を実行し、green確認後に進める。
  - `source /path/to/your/nix/profile.d/nix-daemon.sh`
  - `ci-self up --ref "$(git branch --show-current)"`
- 禁止ブランチ `codex/feat*` は使用しない。

## S32 Completion Definition (S32-30 Exit)

- `COLLECT/NORMALIZE/INDEX/SEARCH_RAG/CITE_RAG` が non-fixture corpus 前提でも deterministic に運用できる。
- compile が「入力意図に応じて profile を選ぶ + 失敗を分類する + 根拠を残す」まで自動化される。
- thread runner の分散実行、failure分類、ops dashboard が日次運用に耐える。
- acceptance/reliability/policy drift/trend の gates が S32 機能込みで green。
- S33 開始条件（残課題、優先度、移行条件）が handoff pack で固定される。

## Workstreams

### WS-A: Retrieval Realism (S32-01..S32-05)

- fixture依存を減らし、実データ寄り corpus を deterministic に扱える状態を作る。

### WS-B: Compile Reliability (S32-06..S32-10)

- compile の profile選択、失敗分類、再現性を運用しやすい形へ拡張する。

### WS-C: Runner Scale & Observability (S32-11..S32-15)

- 大規模実行と障害調査の導線を運用者目線で強化する。

### WS-D: Quality Gates vNext (S32-16..S32-20)

- SLO/acceptance/policy drift/reliability を S32 実装に追随させる。

### WS-E: IL UX vNext (S32-21..S32-25)

- IL authoring と daily operations の操作負荷をさらに下げる。

### WS-F: Release and Handoff (S32-26..S32-30)

- 回帰防止、リリース判断、closeout、S33 handoff を固定する。

## Task Matrix (S32-01..S32-30)

| ID | Title | Primary Deliverable | Acceptance Snapshot | Depends |
| --- | --- | --- | --- | --- |
| S32-01 | Non-fixture Corpus Collect v1 | `src/il_executor.py` `COLLECT source=file_jsonl/rss` | fixture 以外でも `COLLECT=OK` が再現 | - |
| S32-02 | Retrieval Ranking v2 | token一致率 + deterministic score | hit順序が corpusサイズに依らず安定 | 01 |
| S32-03 | Citation Provenance v2 | cite に snippet/hash/source_path 追加 | cite の監査可能性が上がる | 02 |
| S32-04 | Corpus Policy Filter | denylist/size/lang フィルタ | unsafe/ノイズ文書を fail-closed で除外 | 01-03 |
| S32-05 | Retrieval Eval Wall v1 | `scripts/ops/s32_retrieval_eval_wall.py` | non-fixture corpus の品質壁が可視化 | 01-04 |
| S32-06 | Compile Profile Auto-Select | request特性で profile 自動選択 | 手動 profile 指定なしでも品質維持 | - |
| S32-07 | Compile Confidence Contract | confidence + rationale artifact | low confidence の扱いが明確 | 06 |
| S32-08 | Compile Parse Repair Guard v3 | bounded repair + strict boundary | parse誤成功が減り失敗理由が明瞭 | 06-07 |
| S32-09 | Prompt Loop Dataset v2 | compile tune 用ケース拡充 | 改善比較が定量化される | 06-08 |
| S32-10 | Compile Doctor v2 | `scripts/il_doctor.py` compile診断拡張 | compile起因障害を1回で特定可能 | 06-09 |
| S32-11 | Shard Orchestrator v1 | 複数 shard を一括起動/回収するCLI | 手動 shard 管理が不要になる | - |
| S32-12 | Artifact Lease/Lock Guard | shard衝突防止 lock | 並列実行で成果物破損しない | 11 |
| S32-13 | Retry Policy Matrix | error code別 retry/backoff ルール | retry の過不足が減る | 11-12 |
| S32-14 | Failure Digest Classifier v2 | root-cause class 自動付与 | 復旧優先度が即判断できる | 11-13 |
| S32-15 | Operator Dashboard Export | run summary の machine-readable export | ops向けダッシュボード入力が整う | 11-14 |
| S32-16 | Latency Budget/SLO Guard | compile/entry/thread の budget 監査 | latency逸脱を継続検知 | 05,15 |
| S32-17 | Acceptance Wall v6 | S32追加契約を検証 | 新機能の受入判定が固定される | 05,10,15 |
| S32-18 | Policy Drift Guard v2 | contract/schema/code drift 拡張 | S32追加面の drift を検知 | 17 |
| S32-19 | Reliability Soak v3 | non-fixture/runner分散の長時間計測 | 実運用の劣化傾向を見える化 | 15-18 |
| S32-20 | Evidence Trend Index v7 | S32 evidence 横断 index | 欠損と劣化を時系列で追える | 16-19 |
| S32-21 | IL Opcode Catalog Generator | opcode仕様の自動生成 | 実装とドキュメント乖離を縮小 | 17 |
| S32-22 | ilctl Scenario Commands | `ilctl quickstart/triage` 追加 | 初学者の操作手数が減る | 21 |
| S32-23 | Runbook v3 (Decision Playbooks) | `docs/ops/IL_ENTRY_RUNBOOK.md` 改訂 | 障害時の判断速度を改善 | 22 |
| S32-24 | Workspace Init v2 Templates | domain別雛形テンプレート | 現場導入時の初期セットアップ短縮 | 22-23 |
| S32-25 | Doctor v3 with Fix Hints | `il_doctor` の改善提案出力 | エラーから修復までの往復を短縮 | 22-24 |
| S32-26 | Regression Safety v3 | S22/S23/S31/S32 契約回帰監査 | 既存契約の破壊を継続検知 | 17-25 |
| S32-27 | Release Readiness v2 | go/no-go 判定の統合レポート | リリース可否を1 artifactで説明可能 | 20,26 |
| S32-28 | Closeout Generator v2 | `docs/evidence/s32-28/closeout_latest.*` | S32成果と残課題を固定 | 27 |
| S32-29 | S33 Backlog Seed Pack | S33候補の優先順位付き seed | handoff前の設計材料が揃う | 28 |
| S32-30 | S33 Handoff Pack | `docs/evidence/s32-30/handoff_latest.*` | 次スレッド開始条件が曖昧でない | 29 |

## Planned Impacted Files (Representative)

- Core IL:
  - `src/il_executor.py`
  - `src/il_compile.py`
  - `src/il_validator.py`
- IL scripts:
  - `scripts/il_thread_runner_v2.py`
  - `scripts/il_thread_runner_v2_doctor.py`
  - `scripts/il_doctor.py`
  - `scripts/ilctl.py`
  - `scripts/il_workspace_init.py`
  - `scripts/il_compile_prompt_loop.py`
- Ops scripts (new candidates):
  - `scripts/ops/s32_retrieval_eval_wall.py`
  - `scripts/ops/s32_failure_digest_classifier_v2.py`
  - `scripts/ops/s32_operator_dashboard_export.py`
  - `scripts/ops/s32_latency_slo_guard.py`
  - `scripts/ops/s32_acceptance_wall_v6.py`
  - `scripts/ops/s32_policy_drift_guard_v2.py`
  - `scripts/ops/s32_reliability_soak_v3.py`
  - `scripts/ops/s32_evidence_trend_index_v7.py`
  - `scripts/ops/s32_regression_safety_v3.py`
  - `scripts/ops/s32_release_readiness_v2.py`
  - `scripts/ops/s32_closeout_v2.py`
  - `scripts/ops/s32_handoff_pack.py`
- Docs:
  - `docs/ops/S32-01-S32-30-THREAD-V1_PLAN.md`
  - `docs/ops/S32-01-S32-30-THREAD-V1_TASK.md`
  - `docs/ops/S32-01-S32-30-THREAD-V1_PROMPTS.md`
  - `docs/ops/ROADMAP.md`
  - `docs/ops/IL_ENTRY_RUNBOOK.md`
- Tests:
  - `tests/test_s32_*.py`
  - `tests/test_il_executor.py` (or related executor tests)
  - `tests/test_il_compile.py`
  - `tests/test_il_thread_runner_v2*.py`

## Validation Strategy

軽量（taskごと）:

- `make ops-now`
- `python3 -m unittest -v tests/test_il_compile.py tests/test_il_validator.py`
- `python3 -m unittest -v tests/test_s32_<target>.py`

中量（workstreamごと）:

- `make il-thread-smoke`
- `make il-thread-replay-check`
- `make verify-il-thread-v2`
- `make bench-il-compile`

重量（ship直前）:

- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## 22-16-22-99 Execution Shape

1. PLAN:
   - `S32-01..S32-30` の受入条件と impacted files を先に固定。
2. DO:
   - 依存順で最小差分実装（01 -> 30）。
3. CHECK:
   - 軽量 -> 中量 -> 重量の順で gate 実行。
4. SHIP:
   - コマンドと結果を PR body に固定（`STATUS.md` には書かない）。
