# S31-01-S31-30 THREAD v1 IMPLEMENTATION PROMPTS

Last Updated: 2026-02-27

## Usage

- 1タスク = 1PR を推奨（依存が強いタスクのみ 2件同時可）。
- すべてのタスクで Ritual `22-16-22-99`（PLAN -> DO -> CHECK -> SHIP）を適用する。
- 進捗は `docs/ops/S31-01-S31-30-THREAD-V1_TASK.md` と PR body に記録する。

## S31-01 Prompt — Branch/Track Resolver Hardening

### Objective
- `scripts/ops/current_point.py` が `ops/S31-01--S31-30` のような double-dash thread 名でも `S31` track を誤判定しないようにする。

### Required Changes
1. `detect_track` の正規表現を拡張し、`Sxx-aa--Sxx-bb` と `Sxx-aa-Sxx-bb` の両方を受理。
2. `tests/test_current_point.py` に回帰テストを追加。
3. `make ops-now` 実行時に S31 TASK が解決されることを確認。

### Acceptance Criteria
- `detect_track("ops/S31-01--S31-30")` が `S31-01-S31-30`（または仕様で定義した正規化値）を返す。
- 既存の S25/S28/S30 パターンを壊さない。

### Validation
- `python3 -m unittest -v tests/test_current_point.py`

## S31-02 Prompt — IL Workspace Init

### Objective
- 新規利用者が最初の request/cases/out を手作業で作らずに済むよう、`scripts/il_workspace_init.py` を追加する。

### Required Changes
1. `python3 scripts/il_workspace_init.py --out <dir>` で以下を生成:
   - `request.sample.json`
   - `cases.sample.jsonl`
   - `README.md`（実行手順）
2. `Makefile` に `il-init-workspace` を追加。
3. 正常系テストを `tests/test_s31_workspace_init.py` に追加。

### Acceptance Criteria
- 空ディレクトリから 1コマンドで最小実行雛形が揃う。
- 上書き時は `--force` なしで fail-closed。

### Validation
- `python3 -m unittest -v tests/test_s31_workspace_init.py`

## S31-03 Prompt — IL Formatter CLI

### Objective
- IL JSON を canonical 形式へ統一する `scripts/il_fmt.py` を追加する。

### Required Changes
1. `--check`（差分検知のみ）と `--write`（上書き整形）を実装。
2. `src/il_validator.ILCanonicalizer` を再利用し、重複ロジックを作らない。
3. 複数ファイル入力（glob/列挙）をサポート。

### Acceptance Criteria
- canonical bytes に一致するかを deterministic に判定できる。
- invalid JSON は `ERROR` で path と理由を出す。

### Validation
- `python3 -m unittest -v tests/test_s31_il_fmt.py`

## S31-04 Prompt — IL Lint CLI

### Objective
- 契約違反を実行前に検出する `scripts/il_lint.py` を追加し、`code/path/hint` を統一出力する。

### Required Changes
1. `ILValidator` を利用して lint 結果を JSON と標準出力に出す。
2. `--strict` で warning も error 扱いにできるようにする。
3. 出力スキーマを `IL_LINT_REPORT_v1` として固定。

### Acceptance Criteria
- good fixture で `status=OK`、bad fixture で `status=ERROR`。
- 失敗時に最小1件の actionable hint を出力。

### Validation
- `python3 -m unittest -v tests/test_s31_il_lint.py`

## S31-05 Prompt — IL Doctor Entrypoint

### Objective
- compile/entry/runner/doctor を横断診断する `scripts/il_doctor.py` を追加する。

### Required Changes
1. サブチェック: `env`, `fixtures`, `entry smoke`, `thread smoke`, `artifact doctor`。
2. `docs/evidence` ではなく `.local/obs` に診断成果を保存。
3. `Makefile` に `il-doctor` ターゲット追加。

### Acceptance Criteria
- 1コマンドで現在の IL 実行可否を把握できる。
- 1チェック失敗でも stopless で他チェックを継続。

### Validation
- `python3 -m unittest -v tests/test_s31_il_doctor.py`

## S31-06 Prompt — Compile Error Taxonomy v2

### Objective
- `src/il_compile.py` の error 出力を再分類し、誤解釈しにくい taxonomy へ更新する。

### Required Changes
1. `E_SCHEMA/E_INPUT/E_PARSE/E_VALIDATE/E_MODEL/E_NONDETERMINISTIC` の判定境界を明文化。
2. 同一原因の message/hint を統一し、揺れを減らす。
3. 契約文書 `docs/il/IL_COMPILE_CONTRACT_v1.md` の errors 節を同期更新。

### Acceptance Criteria
- 主要 failure fixture で期待 code が安定して出る。
- test の flaky（message揺れ）が解消。

### Validation
- `python3 -m unittest -v tests/test_il_compile.py`

## S31-07 Prompt — Compile Evidence Enrichment

### Objective
- compile report を「再現調査に十分な情報量」へ強化する。

### Required Changes
1. `il.compile.report.json` に以下を追加:
   - `request_sha256`
   - `prompt_sha256`
   - `artifact_pointer_count`
   - `compile_latency_ms`
2. 既存 consumer を壊さない後方互換を維持。
3. 文書化を `docs/il/IL_COMPILE_CONTRACT_v1.md` に反映。

### Acceptance Criteria
- report だけで再現条件を追跡できる。
- 追加フィールドで determinism 監査が容易になる。

### Validation
- `python3 -m unittest -v tests/test_il_compile.py tests/test_s31_compile_report_v2.py`

## S31-08 Prompt — Local LLM Parse Guard v2

### Objective
- local LLM のレスポンス抽出失敗を減らし、parse failure を明確化する。

### Required Changes
1. `_extract_first_json_object_text` の境界ケース（多重 code block, 前後ゴミ文字）をテスト駆動で強化。
2. JSON repair を行う場合は deterministic な最小修復のみ許可。
3. 修復不可時は `E_PARSE` で fail-closed。

### Acceptance Criteria
- 代表的な malformed response を再現テストで網羅。
- 誤って success 扱いするケースをゼロ化。

### Validation
- `python3 -m unittest -v tests/test_s31_compile_parse_guard.py`

## S31-09 Prompt — Compile Explain Artifact

### Objective
- 人間が一目で理解できる `il.compile.explain.md` を生成する。

### Required Changes
1. compile 成功/失敗ごとに説明テンプレートを分岐。
2. 主要項目: request 概要、選択 provider、fallback 有無、error codes、次アクション。
3. 既存 JSON artifact のみを参照し、推測文は入れない。

### Acceptance Criteria
- 非実装者でも explain だけで次対応を判断できる。
- explain 内容と report/json が矛盾しない。

### Validation
- `python3 -m unittest -v tests/test_s31_compile_explain.py`

## S31-10 Prompt — Bench Baseline Diff Gate

### Objective
- `il_compile_bench` の結果比較を自動化し、prompt/profile 改善を定量判断可能にする。

### Required Changes
1. baseline JSON を入力に差分評価する `scripts/il_compile_bench_diff.py` を追加。
2. compare 指標: `expected_match_rate`, `reproducible_rate`, `fallback_rate`, `objective_score`。
3. `WARN/ERROR` しきい値を CLI 引数で指定可能にする。

### Acceptance Criteria
- 1コマンドで「改善/悪化」を判定できる。
- PR body に貼れる summary を出力。

### Validation
- `python3 -m unittest -v tests/test_s31_compile_bench_diff.py`

## S31-11 Prompt — ANSWER Opcode Deterministic v1

### Objective
- `src/il_executor.py` の `ANSWER` を常時 SKIP から deterministic 実装へ更新する。

### Required Changes
1. 入力: retrieve で得た docs + search_terms。
2. 出力: 再現可能なテンプレ回答（ranking/sorting 固定）を生成。
3. `il.exec.result.json` の `answer` を空文字以外で返せるようにする。

### Acceptance Criteria
- 同一入力で answer が毎回一致。
- retrieve が空のときは理由付き `SKIP` を維持。

### Validation
- `python3 -m unittest -v tests/test_s31_executor_answer.py`

## S31-12 Prompt — RAG Opcode Bridge v1

### Objective
- RAG opcode を stub から bridge 実装に置換し、最小 deterministic pipeline を動かす。

### Required Changes
1. `COLLECT/NORMALIZE/INDEX/SEARCH_RAG/CITE_RAG` を順次処理するハンドラを実装。
2. 重い処理は既存 `scripts/rag_pipeline.py` 呼び出し、もしくは軽量 deterministic モードを追加。
3. step report に入出力サマリを残す。

### Acceptance Criteria
- RAG opcode を含む IL で `SKIP` ではなく実処理結果が出る。
- unavailable 条件は明示理由で fail-closed or skip。

### Validation
- `python3 -m unittest -v tests/test_s31_executor_rag_bridge.py`

## S31-13 Prompt — Opcode Args Schema Guard

### Objective
- opcode ごとの `args` を契約化し、不正入力を早期に `ERROR` 化する。

### Required Changes
1. opcode別 schema validator（必須キー/型/範囲）を追加。
2. report の `reason` に `E_OPCODE_ARGS` 系コードを含める。
3. docs `IL_EXEC_CONTRACT_v1` に args 契約を追記。

### Acceptance Criteria
- 不正 args で silently SKIP せず明示的 ERROR になる。
- 正常ケースの互換性を維持。

### Validation
- `python3 -m unittest -v tests/test_s31_executor_args_guard.py`

## S31-14 Prompt — Retrieve Robustness Pack

### Objective
- retrieve ステップの失敗分類を明確化し、運用で原因を特定しやすくする。

### Required Changes
1. fixture load失敗 / index欠損 / doc欠損 / no-hit を別 reason code で出す。
2. `ctx` に残す中間情報を最小化しつつ診断可能性を維持。
3. regression test を追加。

### Acceptance Criteria
- retrieve 異常時の reason が再現可能に分類される。
- 既存正常系の `OK` 率が維持される。

### Validation
- `python3 -m unittest -v tests/test_s31_retrieve_robustness.py`

## S31-15 Prompt — Execution Budget Guard

### Objective
- 実行暴走を防ぐ budget guard（steps/docs/cites）を導入する。

### Required Changes
1. CLI or IL constraint で `max_steps`, `max_retrieved_docs`, `max_cites` を指定可能化。
2. 超過時は `ERROR` か `SKIP` を契約で固定。
3. report に budget 使用量を記録。

### Acceptance Criteria
- guard が deterministic に作動し、再現テスト可能。
- デフォルト設定で既存テストを破壊しない。

### Validation
- `python3 -m unittest -v tests/test_s31_execution_budget_guard.py`

## S31-16 Prompt — Runner Resume Mode

### Objective
- `scripts/il_thread_runner_v2.py` に `--resume` を追加し、中断実行の再開を可能にする。

### Required Changes
1. `cases.partial.jsonl` を読み、完了済み case を再実行しない。
2. resume 元設定（provider/model/seed等）の整合チェックを実装。
3. 不整合時は resume を拒否して理由を出す。

### Acceptance Criteria
- 中断後 resume で残ケースのみ実行される。
- summary 集計が重複なく正しい。

### Validation
- `python3 -m unittest -v tests/test_s31_runner_resume.py`

## S31-17 Prompt — Runner Shard Mode

### Objective
- ケース大量時の運用効率改善として shard 実行を追加する。

### Required Changes
1. `--shard-index` / `--shard-count` を追加。
2. shard 出力の merge ツールを実装し、最終 `cases.jsonl` を deterministic に再構成。
3. merge 後 summary hash を再計算。

### Acceptance Criteria
- 単体実行と shard+merge で同等結果が得られる。
- shard パラメータ異常は fail-closed。

### Validation
- `python3 -m unittest -v tests/test_s31_runner_shard.py`

## S31-18 Prompt — Runner Quarantine

### Objective
- 問題caseを隔離して全体進行を止めない運用導線を追加する。

### Required Changes
1. `--exclude-case-id` / `--exclude-file` を追加。
2. skip された case を `quarantined` として記録。
3. summary に quarantine 件数を追加。

### Acceptance Criteria
- quarantine 指定 case が確実に実行除外される。
- 除外理由が artifact に残る。

### Validation
- `python3 -m unittest -v tests/test_s31_runner_quarantine.py`

## S31-19 Prompt — Runner Failure Digest

### Objective
- run 終了後に失敗一覧を短時間で読める digest を生成する。

### Required Changes
1. `failure_digest.json` と `failure_digest.md` を生成。
2. 含める項目: case id, compile/entry error code, reason, artifact path。
3. severity（ERROR/WARN）で並び替え。

### Acceptance Criteria
- summary を見なくても digest で復旧優先順が判断できる。
- digest の情報源は `cases.jsonl` のみ（整合性維持）。

### Validation
- `python3 -m unittest -v tests/test_s31_runner_failure_digest.py`

## S31-20 Prompt — Runner Doctor v2

### Objective
- doctor を resume/shard/quarantine/failure_digest 対応へ拡張する。

### Required Changes
1. `scripts/il_thread_runner_v2_doctor.py` に v2 検査項目を追加。
2. `summary` と各artifactの cross-check を増やす。
3. `doctor_summary` の schema を v2 化。

### Acceptance Criteria
- 新機能 artifacts の欠損/不整合を自動検知できる。
- 既存 v1 出力も互換チェック可能。

### Validation
- `python3 -m unittest -v tests/test_il_thread_runner_v2_doctor.py tests/test_s31_runner_doctor_v2.py`

## S31-21 Prompt — IL Acceptance Wall v5

### Objective
- S31 追加機能の受入条件を明文化し、契約として固定する。

### Required Changes
1. `scripts/ops/s31_acceptance_wall_v5.py` を追加。
2. S31-11〜20 の主要契約を assert ではなく JSON判定で評価。
3. `docs/evidence/s31-21/*` を生成。

### Acceptance Criteria
- acceptance artifact で PASS/WARN/ERROR が判定可能。
- 未整備環境は SKIP 理由を明記。

### Validation
- `python3 -m unittest -v tests/test_s31_acceptance_wall_v5.py`

## S31-22 Prompt — IL Regression Safety v2

### Objective
- S22/S23 の既存契約が S31 変更で壊れていないことを保証する。

### Required Changes
1. `scripts/ops/s31_regression_safety_v2.py` を追加。
2. 最低対象: il_entry single-entry law, compile fail-closed, runner determinism。
3. `docs/evidence/s31-22/*` へ結果出力。

### Acceptance Criteria
- 主要退行がある場合は WARN/ERROR を明示。
- 正常時はリリース可否判断に使える summary が出る。

### Validation
- `python3 -m unittest -v tests/test_s31_regression_safety_v2.py`

## S31-23 Prompt — Runner Reliability Soak v2

### Objective
- run モード長時間実行で timeout/retry/quarantine の信頼性を評価する。

### Required Changes
1. `scripts/ops/s31_reliability_soak_v2.py` を追加。
2. 複数runの trend（error率, retry率, timeout率）を集計。
3. `docs/evidence/s31-23/*` を生成。

### Acceptance Criteria
- 最低 run 数に達した時点で PASS/WARN を判定。
- サンプル不足は SKIP ではなく WARN+理由。

### Validation
- `python3 -m unittest -v tests/test_s31_reliability_soak_v2.py`

## S31-24 Prompt — IL Policy Drift Guard

### Objective
- IL contract/schema/code のドリフトを検出する guard を追加する。

### Required Changes
1. 契約文書・schema・実装の整合ポイントを定義。
2. `scripts/ops/s31_policy_drift_guard.py` を実装。
3. baseline JSON を `docs/evidence/s31-24/` に固定。

### Acceptance Criteria
- contract更新漏れ/実装先行漏れを検知できる。
- false positive が運用許容範囲。

### Validation
- `python3 -m unittest -v tests/test_s31_policy_drift_guard.py`

## S31-25 Prompt — IL Evidence Trend Index v6

### Objective
- S31-21..24 の evidence を横断集約し、状態を一目で判断可能にする。

### Required Changes
1. `scripts/ops/s31_evidence_trend_index_v6.py` を追加。
2. latest + history を生成。
3. markdown table に phaseごとの status/last_updated を出す。

### Acceptance Criteria
- 欠損 evidence があれば明示 WARN。
- S31 進捗レビューの一次資料として使える。

### Validation
- `python3 -m unittest -v tests/test_s31_evidence_trend_index_v6.py`

## S31-26 Prompt — Unified IL CLI (`ilctl`)

### Objective
- 日次操作のコマンド分散を減らすため、`scripts/ilctl.py` を追加する。

### Required Changes
1. subcommand: `init/fmt/lint/compile/entry/thread/doctor`。
2. 既存スクリプト呼び出しの thin orchestrator とする。
3. `--help` を日本語/英語混在でも理解しやすい文面に整理。

### Acceptance Criteria
- `python3 scripts/ilctl.py --help` で全導線が確認できる。
- 既存スクリプト互換を壊さない。

### Validation
- `python3 -m unittest -v tests/test_s31_ilctl.py`

## S31-27 Prompt — Makefile Target Unification

### Objective
- `make` の IL系ターゲットを整理し、入口を明確化する。

### Required Changes
1. `il-*` 命名で統一（旧ターゲットは alias で互換維持）。
2. `verify-il` 内の順序と責務をコメントで明示。
3. README か runbook にコマンド早見表を追加。

### Acceptance Criteria
- 新規利用者が `make` 一覧から導線を理解できる。
- CI 利用中ターゲットの破壊なし。

### Validation
- `make verify-il`

## S31-28 Prompt — IL Runbook v2

### Objective
- `docs/ops/IL_ENTRY_RUNBOOK.md` を再編し、失敗時の意思決定を早める。

### Required Changes
1. quickstart（最短3コマンド）を先頭に配置。
2. failure decision tree（compile失敗/entry失敗/runner失敗）を追加。
3. troubleshooting を error code ベースで整理。

### Acceptance Criteria
- runbook だけで初回運用が完了できる。
- S31 追加機能（fmt/lint/doctor/ilctl）を反映。

### Validation
- `python3 -m unittest -v tests/test_s31_runbook_links.py`

## S31-29 Prompt — S31 Closeout Generator

### Objective
- S31 の成果と残課題を closeout artifact として自動生成する。

### Required Changes
1. `scripts/ops/s31_closeout.py` を追加。
2. Before/After 指標（操作手数、error分類、runner運用性）を集計。
3. `docs/evidence/s31-29/closeout_latest.{json,md}` を生成。

### Acceptance Criteria
- PR body に転記可能な closeout summary が出力される。
- unresolved risks が明示される。

### Validation
- `python3 -m unittest -v tests/test_s31_closeout.py`

## S31-30 Prompt — S32 Handoff Pack

### Objective
- S32 へ渡す開始条件・優先順位・未解決課題を deterministic に固定する。

### Required Changes
1. `docs/ops/S32-01-S32-10-THREAD-V1_PLAN.md` の雛形を生成（必要最小限）。
2. `docs/evidence/s31-30/handoff_latest.{json,md}` を作成。
3. ROADMAP に S32 handoff の参照を追加。

### Acceptance Criteria
- S31 完了時に「次に何をやるか」が曖昧でない。
- S32 開始に必要な依存情報が手元で完結する。

### Validation
- `make ops-now`
- `make verify-il`

## Ship Gate Reminder (All S31 Tasks)

- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`
