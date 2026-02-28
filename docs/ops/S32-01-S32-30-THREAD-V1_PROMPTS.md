# S32-01-S32-30 THREAD v1 IMPLEMENTATION PROMPTS

Last Updated: 2026-02-28

## Usage

- 1タスク = 1PR を推奨（依存が強いタスクのみ 2件同時可）。
- すべてのタスクで Ritual `22-16-22-99`（PLAN -> DO -> CHECK -> SHIP）を適用する。
- 進捗は `docs/ops/S32-01-S32-30-THREAD-V1_TASK.md` と PR body に記録する。

## S32-01 Prompt — Non-fixture Corpus Collect v1

### Objective
- `COLLECT` opcode が fixture 以外（ローカル JSONL / RSS）を deterministic に取り込めるようにする。

### Required Changes
1. `src/il_executor.py` の `COLLECT` に `source=file_jsonl` と `source=rss` を追加。
2. 入力 path は repo-root 相対のみ許可（絶対/`..` は reject）。
3. 取り込み件数は `max_docs` と budget の小さい方で制限。
4. 失敗理由を `E_RAG_COLLECT_PATH`, `E_RAG_COLLECT_PARSE`, `E_RAG_COLLECT_SOURCE` に分類。

### Acceptance Criteria
- 同一入力で `collected_count` と doc順序が毎回一致。
- 不正 path / 壊れた入力は fail-closed で理由を返す。

### Validation
- `python3 -m unittest -v tests/test_s32_collect_non_fixture.py`

## S32-02 Prompt — Retrieval Ranking v2

### Objective
- retrieval 順位を「再現可能なスコアリング」に置き換え、doc選定の説明可能性を上げる。

### Required Changes
1. term一致率・doc長正規化・doc_id tie-break を使う deterministic score を実装。
2. `out_summary` に `ranking_version` と `score_preview` を追加。
3. 既存 fixture ケースの互換性を壊さないよう fallback ranker を残す。

### Acceptance Criteria
- corpus サイズが増えても、同一 query で上位doc順序が安定。
- rank計算の根拠が step report で追跡できる。

### Validation
- `python3 -m unittest -v tests/test_s32_retrieval_ranking_v2.py`

## S32-03 Prompt — Citation Provenance v2

### Objective
- cite を「どの証拠断片を使ったか」まで追跡可能にする。

### Required Changes
1. `CITE` / `CITE_RAG` の出力へ `snippet`, `snippet_sha256`, `source_path` を追加。
2. snippet は固定長トリミング + deterministic 抜粋位置（先頭一致）で生成。
3. `docs/il/IL_EXEC_CONTRACT_v1.md` の cites 節を更新。

### Acceptance Criteria
- cite だけで原文断片と source を逆引きできる。
- snippet生成規則が deterministic でテスト可能。

### Validation
- `python3 -m unittest -v tests/test_s32_citation_provenance_v2.py`

## S32-04 Prompt — Corpus Policy Filter

### Objective
- 取り込み文書のノイズ/リスクを IL 実行前段で制御する。

### Required Changes
1. denylist token、最大文字数、許可言語（例: `ja/en`）の policy を追加。
2. policy適用結果（accepted/rejected counts）を `out_summary` へ記録。
3. 拒否理由コードを `E_RAG_POLICY_DENYLIST`, `E_RAG_POLICY_SIZE`, `E_RAG_POLICY_LANG` で統一。

### Acceptance Criteria
- policy適用が on/off で可逆的に確認できる。
- reject された文書が後続 `INDEX/SEARCH_RAG` に混入しない。

### Validation
- `python3 -m unittest -v tests/test_s32_corpus_policy_filter.py`

## S32-05 Prompt — Retrieval Eval Wall v1

### Objective
- non-fixture corpus 前提の retrieval 品質を継続監視する acceptance 壁を追加する。

### Required Changes
1. `scripts/ops/s32_retrieval_eval_wall.py` を作成。
2. 指標: hit_rate@k, citation_coverage, policy_reject_rate, no_hit_rate。
3. `docs/evidence/s32-05/retrieval_eval_wall_latest.{json,md}` を出力。

### Acceptance Criteria
- retrieval 品質の PASS/WARN/ERROR が artifact で判定できる。
- サンプル不足は `WARN` と理由を明示。

### Validation
- `python3 -m unittest -v tests/test_s32_retrieval_eval_wall.py`

## S32-06 Prompt — Compile Profile Auto-Select

### Objective
- request の性質に応じて compile prompt profile を自動選択し、運用者の手動判断を減らす。

### Required Changes
1. `src/il_compile.py` に profile selector を追加（manual override は維持）。
2. selector 入力: request text length, artifact_pointer count, strictness hints。
3. report に `profile_selected_by` と `profile_select_reason` を追加。

### Acceptance Criteria
- `--prompt-profile` 未指定でも再現可能な選択結果が出る。
- 明示指定時は selector をバイパスできる。

### Validation
- `python3 -m unittest -v tests/test_s32_compile_profile_autoselect.py`

## S32-07 Prompt — Compile Confidence Contract

### Objective
- compile 結果の信頼度を定量化し、低信頼ケースを運用で扱いやすくする。

### Required Changes
1. compile report に `confidence` (0.0-1.0) と `confidence_factors[]` を追加。
2. low confidence 判定しきい値を CLI/env で設定可能化。
3. `docs/il/IL_COMPILE_CONTRACT_v1.md` に confidence の意味を追記。

### Acceptance Criteria
- 同一入力で confidence 値が安定。
- low confidence を warning として識別可能。

### Validation
- `python3 -m unittest -v tests/test_s32_compile_confidence_contract.py`

## S32-08 Prompt — Compile Parse Repair Guard v3

### Objective
- JSON repair を「必要最小限」に限定し、誤成功を減らす。

### Required Changes
1. repair許可ルール（括弧閉じ不足、末尾カンマ除去など）を明示リスト化。
2. ルール外修復は `E_PARSE` で fail-closed。
3. report に `repair_applied`, `repair_rule_id` を記録。

### Acceptance Criteria
- permissive になりすぎず、再現可能な repair のみ成功。
- malformed response の誤成功率が下がる。

### Validation
- `python3 -m unittest -v tests/test_s32_compile_parse_repair_v3.py`

## S32-09 Prompt — Prompt Loop Dataset v2

### Objective
- compile チューニング用データセットを拡充し、改善を定量で比較可能にする。

### Required Changes
1. `scripts/il_compile_prompt_loop.py` で v2 ケースセットを扱えるようにする。
2. ケースに「難度タグ」「失敗期待コード」を追加。
3. ベンチ結果にタグ別集計（easy/medium/hard）を追加。

### Acceptance Criteria
- profile比較時にタグ別改善/悪化が読み取れる。
- dataset更新時に schema 検証が通る。

### Validation
- `python3 -m unittest -v tests/test_s32_prompt_loop_dataset_v2.py`

## S32-10 Prompt — Compile Doctor v2

### Objective
- `il_doctor` が compile 系の失敗を短時間で切り分けられるようにする。

### Required Changes
1. compile専用チェック（schema, profile選択, parse repair, confidence）を追加。
2. doctor summary に `compile_health` セクションを追加。
3. 失敗時に「次の確認コマンド」を提案する hint を出力。

### Acceptance Criteria
- compile問題の一次切り分けが doctor 1回で完結。
- stopless 実行方針を維持。

### Validation
- `python3 -m unittest -v tests/test_s32_compile_doctor_v2.py`

## S32-11 Prompt — Shard Orchestrator v1

### Objective
- shard 実行の起動・待機・merge を単一コマンド化し、分散運用を簡素化する。

### Required Changes
1. `scripts/il_thread_runner_v2.py` か companion CLI に orchestrator モードを追加。
2. `--shard-count N` 時に N shard の実行計画を生成。
3. 完了後の merge と summary 作成を自動化。

### Acceptance Criteria
- 手動で shard command を組み立てなくてよい。
- 単体実行と orchestrator 実行の集計が一致。

### Validation
- `python3 -m unittest -v tests/test_s32_runner_shard_orchestrator.py`

## S32-12 Prompt — Artifact Lease/Lock Guard

### Objective
- 複数 shard が同一 out_dir を触っても artifact を破損しないようにする。

### Required Changes
1. lock file（例: `.lock`）で writer lease を導入。
2. timeout 付き lease acquisition と stale lock cleanup を実装。
3. lock競合は `E_ARTIFACT_LOCK` で分類。

### Acceptance Criteria
- 同時実行時の JSONL 破損・上書き競合が発生しない。
- lock失敗時の理由が明確。

### Validation
- `python3 -m unittest -v tests/test_s32_artifact_lock_guard.py`

## S32-13 Prompt — Retry Policy Matrix

### Objective
- entry/compile の retry を error code 連動で制御し、過剰リトライを抑える。

### Required Changes
1. retriable/non-retriable の policy table を追加。
2. exponential backoff を deterministic seed で固定。
3. summary に retry attempts と final reason を追加。

### Acceptance Criteria
- non-retriable error で無駄な再試行をしない。
- retriable error は上限内で再試行される。

### Validation
- `python3 -m unittest -v tests/test_s32_retry_policy_matrix.py`

## S32-14 Prompt — Failure Digest Classifier v2

### Objective
- failure digest を root-cause ベースに再編成し、復旧優先順位を上げる。

### Required Changes
1. class 軸: `INPUT`, `COMPILE`, `ENTRY`, `RETRIEVE`, `RAG`, `INFRA` を追加。
2. digest JSON/MD に class別件数と代表ケースを出力。
3. 既存 `failure_digest` との互換（旧フィールド残し）を維持。

### Acceptance Criteria
- digestを見ただけで調査開始点が決まる。
- class分類が deterministic かつ再テスト可能。

### Validation
- `python3 -m unittest -v tests/test_s32_failure_digest_classifier_v2.py`

## S32-15 Prompt — Operator Dashboard Export

### Objective
- 日次運用で使う統計を machine-readable JSON に集約する。

### Required Changes
1. `scripts/ops/s32_operator_dashboard_export.py` を追加。
2. 指標: throughput, success_rate, skip_breakdown, retry_rate, p95_latency。
3. `docs/evidence/s32-15/operator_dashboard_latest.json` を生成。

### Acceptance Criteria
- ダッシュボード入力向けの安定schemaが得られる。
- 欠損データがある場合は reason 付きで出力。

### Validation
- `python3 -m unittest -v tests/test_s32_operator_dashboard_export.py`

## S32-16 Prompt — Latency Budget/SLO Guard

### Objective
- compile/entry/thread 各段の latency 逸脱を継続監視できるようにする。

### Required Changes
1. budget設定（p50/p95/timeout）を受け取り、run結果を判定。
2. `scripts/ops/s32_latency_slo_guard.py` を追加。
3. 出力に breach件数、worstケース、推奨アクションを含める。

### Acceptance Criteria
- しきい値超過を PASS/WARN/ERROR で再現可能に判定。
- false positive を減らすため最小サンプル数条件を持つ。

### Validation
- `python3 -m unittest -v tests/test_s32_latency_slo_guard.py`

## S32-17 Prompt — Acceptance Wall v6

### Objective
- S32 追加機能を受入契約として固定する。

### Required Changes
1. `scripts/ops/s32_acceptance_wall_v6.py` を追加。
2. S32-01..16 の主要契約を JSON判定で評価。
3. `docs/evidence/s32-17/acceptance_wall_v6_latest.{json,md}` を生成。

### Acceptance Criteria
- S32機能の健全性を単一artifactで確認できる。
- 環境依存不足は SKIP/WARN 理由を明示。

### Validation
- `python3 -m unittest -v tests/test_s32_acceptance_wall_v6.py`

## S32-18 Prompt — Policy Drift Guard v2

### Objective
- S32で増えた契約面（collect source, confidence, classifier など）の drift を検知する。

### Required Changes
1. `scripts/ops/s32_policy_drift_guard_v2.py` を追加。
2. contract/schema/code の対応表を更新。
3. baseline を `docs/evidence/s32-18/policy_drift_baseline_v2.json` へ固定。

### Acceptance Criteria
- docs未更新・実装先行の双方を検知。
- drift report が差分レビューに使える粒度を持つ。

### Validation
- `python3 -m unittest -v tests/test_s32_policy_drift_guard_v2.py`

## S32-19 Prompt — Reliability Soak v3

### Objective
- non-fixture corpus + shard運用での長時間安定性を定量把握する。

### Required Changes
1. `scripts/ops/s32_reliability_soak_v3.py` を追加。
2. 指標: run_success_rate, retry_rate, timeout_rate, lock_conflict_rate。
3. trend history を保持し、劣化検知ルールを追加。

### Acceptance Criteria
- 長時間運用の劣化傾向を artifact で追跡可能。
- サンプル不足時は WARN 扱いにして理由を残す。

### Validation
- `python3 -m unittest -v tests/test_s32_reliability_soak_v3.py`

## S32-20 Prompt — Evidence Trend Index v7

### Objective
- S32 quality artifacts を横断集約し、レビュー一次資料を自動生成する。

### Required Changes
1. `scripts/ops/s32_evidence_trend_index_v7.py` を追加。
2. latest + history を `docs/evidence/s32-20/` に出力。
3. 欠損 evidence を WARN として明示。

### Acceptance Criteria
- S32の品質状態を1つの index で把握できる。
- 時系列比較が可能。

### Validation
- `python3 -m unittest -v tests/test_s32_evidence_trend_index_v7.py`

## S32-21 Prompt — IL Opcode Catalog Generator

### Objective
- 実装されている opcode 仕様を自動抽出し、利用者向けカタログを生成する。

### Required Changes
1. `_OPCODE_HANDLERS` と args spec を走査して catalog JSON/MD を生成。
2. `docs/ops` または `docs/il` に出力先を固定。
3. 不明 opcode/ドキュメント欠落を警告。

### Acceptance Criteria
- 実装とドキュメントのズレが減る。
- opcode追加時に catalog 更新が機械化される。

### Validation
- `python3 -m unittest -v tests/test_s32_opcode_catalog_generator.py`

## S32-22 Prompt — ilctl Scenario Commands

### Objective
- `ilctl` に業務シナリオ単位のコマンドを追加し、利用導線を短縮する。

### Required Changes
1. `quickstart`, `triage`, `verify-pack` などの高頻度シナリオをサブコマンド化。
2. 既存 `init/fmt/lint/compile/entry/thread/doctor` への thin orchestrator を維持。
3. `--help` を用途別に再編。

### Acceptance Criteria
- 初回利用者が `ilctl --help` だけで最短導線を把握できる。
- 既存コマンド互換を壊さない。

### Validation
- `python3 -m unittest -v tests/test_s32_ilctl_scenarios.py`

## S32-23 Prompt — Runbook v3 (Decision Playbooks)

### Objective
- 失敗パターン別の復旧手順を runbook に固定し、判断時間を短縮する。

### Required Changes
1. `docs/ops/IL_ENTRY_RUNBOOK.md` に playbook 章を追加。
2. シナリオ: compile parse失敗 / no-hit / lock競合 / retry飽和 / latency breach。
3. 各シナリオに「確認コマンド -> 判断条件 -> 次アクション」を記載。

### Acceptance Criteria
- runbook 単体で triage が実行できる。
- playbook が S32追加エラーコードと整合。

### Validation
- `python3 -m unittest -v tests/test_s32_runbook_playbooks.py`

## S32-24 Prompt — Workspace Init v2 Templates

### Objective
- domain別テンプレートで IL 初期セットアップを高速化する。

### Required Changes
1. `scripts/il_workspace_init.py` に `--template` オプションを追加。
2. テンプレート例: `faq`, `incident`, `research`。
3. 各テンプレートで sample request/cases/README を生成。

### Acceptance Criteria
- template 切替で用途別の初期ファイルが再現可能に生成される。
- 未知テンプレート指定は fail-closed。

### Validation
- `python3 -m unittest -v tests/test_s32_workspace_init_templates_v2.py`

## S32-25 Prompt — Doctor v3 with Fix Hints

### Objective
- doctor 出力に「修正提案」を追加し、調査から修正までの往復を減らす。

### Required Changes
1. `scripts/il_doctor.py` の各チェックに hint rule を付与。
2. summary に `fix_hints[]` と `next_commands[]` を追加。
3. hint は事実ベース（logから抽出）で、推測文を入れない。

### Acceptance Criteria
- doctor 実行後に次の具体的行動が即決できる。
- hint の誤誘導を抑えるため rule-based で生成。

### Validation
- `python3 -m unittest -v tests/test_s32_doctor_v3_fix_hints.py`

## S32-26 Prompt — Regression Safety v3

### Objective
- S22/S23/S31/S32 の主要契約を横断監査し、破壊的退行を防ぐ。

### Required Changes
1. `scripts/ops/s32_regression_safety_v3.py` を追加。
2. 監査対象を matrix化（entry law, compile fail-closed, runner determinism, collect realism）。
3. `docs/evidence/s32-26/regression_safety_v3_latest.{json,md}` を生成。

### Acceptance Criteria
- 主要回帰を WARN/ERROR で再現可能に検知。
- リリース可否の一次判定に使える。

### Validation
- `python3 -m unittest -v tests/test_s32_regression_safety_v3.py`

## S32-27 Prompt — Release Readiness v2

### Objective
- quality artifacts を統合し、go/no-go を1つのレポートで説明できるようにする。

### Required Changes
1. `scripts/ops/s32_release_readiness_v2.py` を追加。
2. 入力: acceptance/policy drift/reliability/latency/trend/regression。
3. 出力: `READY`, `CONDITIONAL_READY`, `BLOCKED` のいずれか。

### Acceptance Criteria
- 判定理由が機械可読 + 人間可読で一致。
- 未収集artifactは `BLOCKED` または `CONDITIONAL_READY` に明示反映。

### Validation
- `python3 -m unittest -v tests/test_s32_release_readiness_v2.py`

## S32-28 Prompt — Closeout Generator v2

### Objective
- S32成果と未解決リスクを closeout artifact として固定する。

### Required Changes
1. `scripts/ops/s32_closeout_v2.py` を追加。
2. Before/After 指標（品質・遅延・運用性）を集計。
3. `docs/evidence/s32-28/closeout_latest.{json,md}` を生成。

### Acceptance Criteria
- S32 の達成度と残課題が PR body に転記しやすい形で出力。
- unresolved risks が空でなくても構造化される。

### Validation
- `python3 -m unittest -v tests/test_s32_closeout_v2.py`

## S32-29 Prompt — S33 Backlog Seed Pack

### Objective
- S33 の初期優先順位を deterministic に生成し、handoff前の曖昧さを減らす。

### Required Changes
1. `scripts/ops/s32_handoff_pack.py` に backlog seed 生成ステップを追加。
2. 入力: closeout risks + trend劣化 + pending ops。
3. 出力: `docs/evidence/s32-29/s33_backlog_seed_latest.{json,md}`。

### Acceptance Criteria
- S33候補が priority/rationale/dependency 付きで生成される。
- 同一入力で順位が安定。

### Validation
- `python3 -m unittest -v tests/test_s32_s33_backlog_seed_pack.py`

## S32-30 Prompt — S33 Handoff Pack

### Objective
- S33 開始条件・優先課題・必須チェックを handoff artifact に固定する。

### Required Changes
1. `docs/evidence/s32-30/handoff_latest.{json,md}` を生成。
2. S33 start conditions（closeout, verify-il, suite）を明記。
3. `docs/ops/ROADMAP.md` の S33 セクションへ参照を追加。

### Acceptance Criteria
- S32終了時に「次に何をやるか」が曖昧でない。
- handoff artifact だけで初動計画が立てられる。

### Validation
- `make ops-now`
- `make verify-il`

## Ship Gate Reminder (All S32 Tasks)

- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`
