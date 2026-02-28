# S31-01-S31-30 THREAD v1 PLAN — IL UX/Capability Expansion

Last Updated: 2026-02-27

## Goal

- IL の不足機能を埋め、`compile -> entry -> thread runner` を「迷わず使える」日次運用導線へ引き上げる。
- S31-30 Exit 時点で、IL authoring/validation/execution/debug の体験を 1 コマンド群で再現可能にする。

## Current Point (2026-02-27)

- Branch: `ops/S31-01--S31-30`
- 直前スレッド: `S30-1-S30-900` 完了（`pending_total=0`）
- 既知ギャップ（実装上の事実）:
  - `src/il_executor.py` の `ANSWER` は常時 `SKIP`
  - `src/il_executor.py` の RAG opcode は stub
  - IL authoring 用の `fmt/lint/init` 系 CLI が未整備
  - thread runner は強いが resume/shard/quarantine が未整備

## Non-negotiables

- Ritual `22-16-22-99` を既定フローとして使う（PLAN -> DO -> CHECK -> SHIP）。
- milestone checks は non-blocking を維持し、milestone-required gate は追加しない。
- `docs/ops/STATUS.md` を進捗 SOT に使わない（TASK + PR body に固定）。
- PR作成/更新前に `ci-self` gate を実行し、green確認後に進める。
  - `source /path/to/your/nix/profile.d/nix-daemon.sh`
  - `ci-self up --ref "$(git branch --show-current)"`
- 禁止ブランチ `codex/feat*` は使用しない。

## S31 Completion Definition (S31-30 Exit)

- IL利用者が最短導線 `init -> compile -> lint/fmt -> entry -> runner -> doctor` を迷わず実行できる。
- 実行体（executor）で `ANSWER` と RAG opcode が「stub ではない deterministic 実装」になる。
- compile/report/runner artifact が「失敗理由を 1 回で判読できる粒度」に改善される。
- thread runner に `resume`, `shard`, `quarantine` の運用導線が追加される。
- `verify-il` と `verify-il-thread-v2` が S31 変更込みで green。

## Workstreams

### WS-A: Authoring UX (S31-01..S31-05)

- 作る人が最初につまずく点（テンプレ不足、整形不足、lint不足、入口不明確）を除去する。

### WS-B: Compile Explainability (S31-06..S31-10)

- compile の失敗理由・再現性・プロンプト品質を可視化し、調整の往復回数を下げる。

### WS-C: Executor Capability (S31-11..S31-15)

- 未実装/弱実装 opcode を deterministic 方針で強化し、実行品質を上げる。

### WS-D: Runner Operability (S31-16..S31-20)

- 長時間運用で効く機能（再開、分割、隔離、失敗サマリ、doctor v2）を追加する。

### WS-E: Quality & Readiness (S31-21..S31-25)

- S31 追加機能を acceptance/reliability/policy drift/evidence trend で固定する。

### WS-F: DX Finish & Handoff (S31-26..S31-30)

- コマンド面・runbook面・closeout面を仕上げ、S32 へ渡せる状態にする。

## Task Matrix (S31-01..S31-30)

| ID | Title | Primary Deliverable | Acceptance Snapshot | Depends |
| --- | --- | --- | --- | --- |
| S31-01 | Branch/Track Resolver Hardening | `current_point` が `ops/S31-01--S31-30` を正しく解決 | `detect_track` の回帰テスト追加 | - |
| S31-02 | IL Workspace Init | `scripts/il_workspace_init.py` で request/cases/out 雛形生成 | 1コマンドで雛形一式生成 | 01 |
| S31-03 | IL Formatter CLI | `scripts/il_fmt.py` (check/write) | canonical diff が安定 | 02 |
| S31-04 | IL Lint CLI | `scripts/il_lint.py` (code/path/hint) | 失敗理由が structured で出る | 03 |
| S31-05 | IL Doctor Entrypoint | `scripts/il_doctor.py` + `make il-doctor` | doctor 1回で主要導線診断 | 02-04 |
| S31-06 | Compile Error Taxonomy v2 | `src/il_compile.py` エラー整備 | `E_*` と hint が再分類 | 04 |
| S31-07 | Compile Evidence Enrichment | compile report に hash/inputs snapshot 追加 | 調査時の再現情報が十分 | 06 |
| S31-08 | Local LLM Parse Guard v2 | JSON抽出/repair境界の明確化 | `E_PARSE` の誤判定減少 | 06 |
| S31-09 | Compile Explain Artifact | `il.compile.explain.md` 自動生成 | 人間可読の説明が残る | 07-08 |
| S31-10 | Bench Baseline Diff Gate | ベンチ差分比較スクリプト | profile比較を定量化 | 06-09 |
| S31-11 | ANSWER Opcode Deterministic v1 | `ANSWER` を stub から脱却 | `overall_status=OK` で answer 生成 | 04 |
| S31-12 | RAG Opcode Bridge v1 | RAG opcode の deterministic bridge | RAG系 opcode が stub でない | 11 |
| S31-13 | Opcode Args Schema Guard | opcode引数の型/必須チェック | 不正 args を fail-closed | 11-12 |
| S31-14 | Retrieve Robustness Pack | fixture/lookup エラー分類強化 | retrieve失敗理由の分類固定 | 13 |
| S31-15 | Execution Budget Guard | docs/cites/step budget 制約追加 | runaway 防止が働く | 13-14 |
| S31-16 | Runner Resume Mode | `--resume` で partial から再開 | 中断後に再処理を最小化 | 05 |
| S31-17 | Runner Shard Mode | ケース分割実行 + deterministic merge | 大規模実行時間を短縮 | 16 |
| S31-18 | Runner Quarantine | `--exclude-case-id` 等で隔離運用 | 問題ケース分離が容易 | 16 |
| S31-19 | Runner Failure Digest | `failure_digest.md/json` 生成 | 失敗原因把握が高速化 | 16-18 |
| S31-20 | Doctor v2 for Runner | doctor の検査範囲拡張 | resume/shard/quarantine成果物監査 | 16-19 |
| S31-21 | IL Acceptance Wall v5 | S31仕様の受入テスト壁 | 主要契約が網羅される | 11-20 |
| S31-22 | IL Regression Safety v2 | 既存契約の回帰防止強化 | S22/S23 契約が壊れない | 21 |
| S31-23 | Runner Reliability Soak v2 | 長時間 run の再現性計測 | timeout/retry 傾向を可視化 | 16-22 |
| S31-24 | IL Policy Drift Guard | contract/schema/code の drift 検知 | drift を fail-fast で検出 | 21-23 |
| S31-25 | IL Evidence Trend Index v6 | S31 evidence の横断 index | 欠損・劣化が一目でわかる | 21-24 |
| S31-26 | Unified IL CLI (`ilctl`) | `scripts/ilctl.py` で主要操作集約 | コマンド学習コストを削減 | 05,10,20 |
| S31-27 | Makefile/Target Unification | `make il-*` 命名統一 | daily ops 入口が簡潔 | 26 |
| S31-28 | IL Runbook v2 | decision tree + troubleshooting 更新 | 新規参加者が迷わない | 26-27 |
| S31-29 | S31 Closeout Generator | closeout artifact 自動生成 | Before/After と残課題を固定 | 21-28 |
| S31-30 | S32 Handoff Pack | handoff plan/task と移行条件固定 | 次スレッド開始条件が明確 | 29 |

## Planned Impacted Files (Representative)

- Core IL:
  - `src/il_compile.py`
  - `src/il_executor.py`
  - `src/il_validator.py`
- IL scripts:
  - `scripts/il_compile.py`
  - `scripts/il_entry.py`
  - `scripts/il_thread_runner_v2.py`
  - `scripts/il_thread_runner_v2_doctor.py`
  - `scripts/il_compile_bench.py`
  - `scripts/il_compile_prompt_loop.py`
  - `scripts/il_thread_runner_v2_suite.py`
  - `scripts/il_workspace_init.py` (new)
  - `scripts/il_fmt.py` (new)
  - `scripts/il_lint.py` (new)
  - `scripts/il_doctor.py` (new)
  - `scripts/ilctl.py` (new)
- Ops/docs:
  - `scripts/ops/current_point.py`
  - `docs/ops/S31-01-S31-30-THREAD-V1_PLAN.md`
  - `docs/ops/S31-01-S31-30-THREAD-V1_TASK.md`
  - `docs/ops/S31-01-S31-30-THREAD-V1_PROMPTS.md`
  - `docs/ops/ROADMAP.md`
  - `docs/ops/IL_ENTRY_RUNBOOK.md`
  - `docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md`
  - `docs/il/IL_COMPILE_CONTRACT_v1.md`
  - `docs/il/IL_EXEC_CONTRACT_v1.md`
- Tests:
  - `tests/test_current_point.py`
  - `tests/test_il_compile.py`
  - `tests/test_il_validator.py`
  - `tests/test_il_thread_runner_v2.py`
  - `tests/test_il_thread_runner_v2_doctor.py`
  - `tests/test_il_thread_runner_v2_suite.py`
  - `tests/test_il_compile_bench.py`
  - `tests/test_il_entry_outdir.py`
  - `tests/test_s31_*.py` (new)

## Validation Strategy

軽量（taskごと）:

- `make ops-now`
- `python3 -m unittest -v tests/test_current_point.py`
- `python3 -m unittest -v tests/test_il_compile.py tests/test_il_validator.py`

中量（workstreamごと）:

- `make il-thread-smoke`
- `make il-thread-replay-check`
- `make verify-il-thread-v2`
- `make bench-il-compile`

重量（ship直前）:

- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## 22-16-22-99 Execution Shape

1. PLAN:
   - `S31-01..S31-30` の受入条件と impacted files を先に固定。
2. DO:
   - 依存順で最小差分実装（01 -> 30）。
3. CHECK:
   - 軽量 -> 中量 -> 重量の順で gate 実行。
4. SHIP:
   - コマンドと結果を PR body に固定（`STATUS.md` には書かない）。
