# S25-02 Work Breakdown Matrix — PR Units and Measurement Contract

Last Updated: 2026-02-26

## Purpose

- S25 を PR 単位に分割し、「どの PR で何を測るか」を先に固定する。
- 後続の ML / RAG / LangChain 実装で、比較不能な変更混線を防ぐ。

## Baseline Anchor (from S25-03)

- Baseline JSON: `docs/evidence/s25-03/baseline_latest.json`
- Baseline Markdown: `docs/evidence/s25-03/baseline_latest.md`
- Reference metrics:
  - quality: 5/5 commands passed
  - eval pass rate: 100.0%
  - speed(total): 0.492 sec
  - cost(command count): 5

## PR Units

| PR Unit | Phase | Goal | Planned TouchSet | What To Measure (PR body required) | Exit Gate |
|---|---|---|---|---|---|
| PR-A | S25-04 Observability | 観測形式とログ格納先を固定 | `scripts/ops/*`, `docs/ops/*`, `docs/evidence/s25-03/*` | `OK/WARN/ERROR/SKIP` 行が最低1行ずつ残るか、観測ログ保存先が固定されているか | `make ops-now`, `python3 scripts/ops/s25_baseline_freeze.py` |
| PR-B | S25-05 Regression Safety | 既存契約の回帰検知を強化 | `ops/*`, `tests/*`, `Makefile`, `docs/ops/*` | `make verify-il` 結果、`ops/required_checks_sot.sh check` の結果、既存契約破壊 0 件 | `make verify-il`, `bash ops/required_checks_sot.sh check` |
| PR-C | S25-06 Acceptance Wall | 完成判定ケースを固定 | `tests/*`, `eval/*`, `docs/ops/*`, `docs/evidence/*` | acceptance case 数、pass/fail 内訳、失敗 taxonomy | `python3 -m unittest -v ...`, `python3 eval/run_eval.py --mode verify-only --provider mock --dataset ...` |
| PR-D | S25-07 ML Experiment Loop | ML 実験テンプレートを固定 | `scripts/*`, `docs/ops/*`, `data/eval/*` | seed/config、1回目 run 指標、baseline 比較差分 | 再実行で同一フォーマット結果が出ること |
| PR-E | S25-08 RAG Tuning Loop | RAG 調整 1 ループを固定 | `scripts/rag_pipeline.py`, `eval/*`, `docs/evidence/*`, `docs/ops/*` | tuning 前後の `pass_rate` / `latency` / failure code 差分 | `python3 eval/run_eval.py ...` の before/after 比較 |
| PR-F | S25-09 LangChain PoC | LangChain 最小接続 + rollback 固定 | `src/*`, `scripts/*`, `docs/ops/*`, `tests/*` | 接続 smoke 成功、rollback 動線の実演結果 | PoC smoke + rollback smoke PASS |
| PR-G | S25-10 Closeout | スレッド完了判定を固定 | `docs/ops/*`, `docs/evidence/*` | Before/After 表、未解決リスク、次スレ handoff | closeout evidence が PR body に揃う |

## Dependency Edges (Serial Contract)

- PR-A -> PR-B
- PR-B -> PR-C
- PR-C -> PR-D
- PR-D -> PR-E
- PR-E -> PR-F
- PR-F -> PR-G

Note:
- Serial を基本にする（1PRで1つの評価意図）。
- 併走は docs-only 更新に限る。

## TouchSet Overlap and Split Rule

- Overlap high:
  - PR-B / PR-C / PR-E / PR-F は `tests`, `scripts`, `docs/ops` が重なる。
- Split decision:
  - overlap あり + measurement intent が異なるため、**1 phase = 1 PR** を固定する。
- Exception:
  - typo/doc wording のみは直近 PR に同梱可（計測値に影響しない範囲）。

## Measurement Contract (Per PR Body)

Each PR must include:

1. Baseline reference:
   - `docs/evidence/s25-03/baseline_latest.json`
2. Commands executed:
   - exact command lines
3. Results:
   - quality / speed / cost
4. Delta vs baseline:
   - better / equal / worse + one-line reason
5. Risk and rollback:
   - immediate rollback command/path

## Canonical PR Body Block (Template)

```md
### S25-0x Measurement
- baseline: docs/evidence/s25-03/baseline_latest.json
- quality: <passed/total>
- speed: <sec>
- cost: <command count or runtime units>
- delta_vs_baseline: <better|equal|worse> (<reason>)
- rollback: <command or file restore strategy>
```
