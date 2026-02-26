# IL Compile Bench Model v1

## Goal
`il_compile` の品質を、status だけでなく「中身の正しさ」で測る。

## Inputs
- each case has:
  - `expected_status` (`OK|ERROR`)
  - optional `required_terms` (gold set)
  - optional `required_opcodes` (gold set)

## Per-case Metrics
`required_terms` / `required_opcodes` それぞれに同じ集合比較を適用。

- gold set: `G`
- predicted set: `P`
- true positive: `TP = |G ∩ P|`
- false positive: `FP = |P - G|`
- false negative: `FN = |G - P|`

Derived:
- precision: `TP / (TP + FP)`
- recall: `TP / (TP + FN)`
- F1: `2PR / (P + R)` (`P+R=0` なら `0`)
- exact match: `G == P`

## Aggregate Metrics
- macro F1: 各ケースF1の平均
- micro F1: 全ケースの `TP/FP/FN` 合算後に算出
- exact match rate: exact一致ケース割合

## Existing Stability Metrics
- `expected_match_rate`
- `il_validity_rate` (expected OK のうち OKになった率)
- `reproducible_rate`
- `fallback_rate`

## Objective Score (Prompt Loop Ranking)
prompt比較では次の重み付きスコアで順位付け:

`score = 0.30*expected_match_rate + 0.20*reproducible_rate + 0.20*(1-fallback_rate) + 0.15*term_micro_f1 + 0.15*opcode_micro_f1`

Primary tie-break:
1. `fallback_count` が小さい方
2. `objective_score` が高い方
3. `expected_match_rate` が高い方
4. `reproducible_rate` が高い方

## Auto Expansion (Deterministic)
- `--expand-factor N` で OKケースを言い換えテンプレートで増やす。
- 同一 `seed` なら増え方は固定（再現可能）。
