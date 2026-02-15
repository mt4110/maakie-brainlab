# PLAN: S17 Milestone - IL-as-LLM Contract v1
Status: DONE
Owner: ambi
Progress: 100%

## Goal（目的）
- LLM 出力を「自然言語」ではなく **検証可能な中間言語（IL: Intermediate Language）**として扱うための契約を定義し、再現性・監査性・決定論を保証する。

## Non-Goal（やらないこと）
- LLM の推論品質向上。
- 生成文の美しさや会話品質の追求。

## Inputs（入力）
- Repo: mt4110/maakie-brainlab

## Outputs（出力）
- S17-01: Contract Spec
- S17-02: Validator Implement
- S17-03: reviewpack Integration

## Invariants（絶対に壊さないもの）
- Determinism: 同一入力・同一ロジックに対して必ず同一の検証結果・正規化出力を得ること。
- Auditability: 変更の証拠（Bundle SHA256）を Ritual 形式で記録すること。

## Stop Conditions（停止条件）
- error: いずれかのフェーズで Gate (verify-only) が FAIL。
- error: 証拠ハッシュの不一致。

## Plan Pseudocode（疑似コード）
### P0: Kickoff (S17-00)
- 目的・用語・進捗定義の固定。

### P1: Spec Layout (S17-01)
- Contract Body / Schema / Fixtures の確定。

### P2: Core Logic (S17-02)
- HARDCORE+ Validator / Canonicalizer の実装。
- Import 契約の固定。

### P3: Toolchain (S17-03)
- reviewpack への統合。
- スケジュール実行の安定化。

## Dead-Angle Check（死角チェック）
- 進捗の主観的評価を排除しているか？ → 均等フェーズ + TASK チェック数比例で自動計算。
- 証拠の改ざん・誤記を防止しているか？ → Ritual shasum コマンドの併記をルール化。
