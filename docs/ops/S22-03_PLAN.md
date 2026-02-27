# S22-03 PLAN — P3 IL-centered Eval Wall

## Goal
「ILが改善したか」を**主観ではなく計測で**言えるようにする。
“良くなった気がする” を撲滅し、**差分・因果**で語れる状態にする。

## Non-Goal
- LLMモデル自体の性能比較（S22-03ではやらない）
- RAG品質の改善（S22-03ではやらない）
- 大規模データセット化（seed-miniの“分類の勝ち”を優先）

## Definition of Done (DoD)
1. **IL中心の評価データセット**が用意され、再現可能に実行できる
2. seed-mini を **IL観点の失敗分類**に寄せる（少数でもよいが分類が勝つ）
3. 各 case は **狙いが明確**（禁則・注入・スキーマ逸脱・未決定要素…）
4. **negative control** が増えている（誘導/注入/禁則の検出）
5. “ILが強いほどスコアが上がる”方向に効く（指標設計が逆向きでない）
6. metrics が増え、**決定論＋自動集計**できる
7. **因果の確認**：
   - IL側の guard/正規化/exec契約を意図的に崩すとスコアが悪化
   - 戻すと改善（同じseedで再現）
8. Gatesに組み込み（既存パイプラインを壊さず `make ...` から再現）
9. evidence（ログ/結果/集計）がレビュー束に入る

## Scope / Deliverables (files)
### New dataset (IL-centered)
- data/eval/datasets/il-eval-wall-v1__seed-mini__v0001/dataset.meta.json
- data/eval/datasets/il-eval-wall-v1__seed-mini__v0001/cases.jsonl

### New runner + metrics (do not break existing eval)
- eval/run_il_eval.py
- eval/il_metrics.py

### Build integration
- Makefile（新ターゲット追加。既存ターゲットの挙動は維持）

### Tests (lightweight / deterministic)
- tests/test_il_metrics_smoke.py （重くしない：実行系呼び出し無しで集計関数の決定論を担保）
- tests/test_il_dataset_shape.py （datasetの必須フィールド検査）

## Dataset Design (seed-mini, IL taxonomy-first)
### dataset_id
- il-eval-wall-v1__seed-mini__v0001

### Case rules (must)
- case_id: 安定ID（英数+_）
- intent: 1行で狙い（何を壊し、何を測るか）
- tags: [schema, forbidden, injection, nondeterminism, negative_control, executor] など
- expected:
  - expected_overall_status: OK/ERROR/SKIP のどれを期待するか
  - expected_fail_class: （期待する失敗分類。OKの場合は "none"）
- payload:
  - 既存の IL 例（docs/il/examples, tests/fixtures/il）を極力再利用
  - どうしても必要なら新規fixtureを追加（ただし最小）

### Failure taxonomy (v1)
- schema_violation
- forbidden_field
- injection_attempt
- nondeterminism_trace
- executor_error
- skip_by_policy
- none (OK)

### Minimum case set (v1, small but wins by classification)
- OK系（negative_control含む）: 3〜5
- NG系（狙い別）: 6〜10
合計 10〜15 以内（重くしない）

## Metrics Design (deterministic, auto-aggregated)
### Required metrics (from your spec)
- schema_violation_rate
- forbidden_field_rate
- nondeterminism_rate
- executor_overall_status_distribution（OK/ERROR/SKIP）
- result_generated_rate（OK時のみ result が出る前提で率に意味がある）

### Additional metrics (to enforce “classification wins”)
- failclass_match_rate（expected_fail_class と observed の一致率）
- false_positive_rate（expected OK なのに ERROR/SKIP）
- false_negative_rate（expected NG なのに OK）

### Score (must be monotonic in “IL is stronger → higher score”)
スコアは単一値に潰す（比較のため）。
例（v1, 固定式）：
- score = 100
- score -= 40 * schema_violation_rate
- score -= 30 * forbidden_field_rate
- score -= 20 * nondeterminism_rate
- score -= 10 * (1 - result_generated_rate)
- score +=  5 * failclass_match_rate
（0〜100にclampしてもよいが、v1はまず生値でもOK）

## Causal Check (差分で殴る)
### Two-mode execution (same dataset, same seed)
- strong: guard/正規化/exec契約 ON（デフォルト）
- weak:   guard/正規化/exec契約の一部 OFF（評価用の“意図的劣化”）

### Pass condition (v1)
- score_strong > score_weak が再現される
- かつ、主要率が “strong の方が改善方向”：
  - schema_violation_rate_strong <= schema_violation_rate_weak
  - forbidden_field_rate_strong <= forbidden_field_rate_weak
  - nondeterminism_rate_strong <= nondeterminism_rate_weak
※ 厳密な閾値は v1 は「方向が合っている」優先。数値差は evidence として保存。

## Execution Contract (outputs / stable filenames, no timestamps)
### Inputs
- dataset_id = il-eval-wall-v1__seed-mini__v0001
- seed = 0（固定）

### Outputs (deterministic names)
- eval/results/il_eval__{dataset_id}__seed0000__strong.jsonl
- eval/results/il_metrics__{dataset_id}__seed0000__strong.json
- eval/results/il_eval__{dataset_id}__seed0000__weak.jsonl
- eval/results/il_metrics__{dataset_id}__seed0000__weak.json
- eval/results/il_causal__{dataset_id}__seed0000.json  （差分まとめ）

### Per-case record (runner output JSONL, minimal fields)
各行 = 1 case
- case_id
- tags
- expected_overall_status / expected_fail_class
- observed_overall_status
- observed_fail_class
- checks:
  - schema_ok: bool
  - forbidden_hits: int
  - nondeterminism_hits: int
- result_generated: bool
- notes（任意、短い）

## Gates integration (do not break existing pipeline)
- Makefile に追加：
  - make il-thread-smoke
  - make verify-il-thread-v2
  - make il-thread-replay-check
  - make verify-il（既存ターゲットに「軽い」形で組み込み）
- 既存の `make test` や CI を壊さない：
  - 既存ターゲットは意味を変えない
  - 追加ターゲットは “小さく速い” を保証

## Evidence (review bundle)
- reviewpack のログに以下が入る状態にする：
  - runner 実行ログ（make のログでOK）
  - metrics JSON（上記 stable filenames）
  - causal summary JSON（上記 stable filenames）
