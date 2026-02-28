# S31-01-S31-30 THREAD v1 TASK — IL UX/Capability Expansion

Last Updated: 2026-02-27

## Progress

- S31-01-S31-30 v1: 100% (S31-01..S31-30 implemented; evidence/closeout/handoff generated)

## Current Facts

- S30 は完了済み、S31 は新規 thread。
- S31 の主眼は `IL の不足機能` と `使い勝手` の同時改善。
- 進捗 SOT はこの TASK + PR body（`docs/ops/STATUS.md` は使わない）。
- 実装プロンプトは `docs/ops/S31-01-S31-30-THREAD-V1_PROMPTS.md` を参照。

## Ritual 22-16-22-99

- PLAN: `docs/ops/S31-01-S31-30-THREAD-V1_PLAN.md` で受入条件と依存を固定
- DO: 依存順で最小実装
- CHECK: 軽量 -> 中量 -> 重量 gate
- SHIP: test command/result を PR body に固定

## Checklist

### Phase-1: Authoring UX (S31-01..S31-05)

- [x] S31-01 `current_point` が `ops/S31-01--S31-30` を正しく判定し、TASK解決を安定化
- [x] S31-02 `scripts/il_workspace_init.py` を追加し、request/cases/out の雛形を1コマンド生成
- [x] S31-03 `scripts/il_fmt.py` を追加し、`--check/--write` で canonical formatting
- [x] S31-04 `scripts/il_lint.py` を追加し、structured lint errors（code/path/hint）を出力
- [x] S31-05 `scripts/il_doctor.py` + `make il-doctor` を追加し、IL導線の総合診断を可能化

### Phase-2: Compile Explainability (S31-06..S31-10)

- [x] S31-06 compile error taxonomy v2（`E_*` 整理 + hint改善）
- [x] S31-07 compile report へ hash/input snapshot/fallback reason を拡充
- [x] S31-08 local LLM response parse guard v2（抽出境界と fail-closed の明確化）
- [x] S31-09 `il.compile.explain.md` を生成し、失敗理由・入力・次アクションを要約
- [x] S31-10 bench baseline diff gate（profile差分の定量比較）を追加

### Phase-3: Executor Capability (S31-11..S31-15)

- [x] S31-11 `ANSWER` opcode の deterministic 実装（stub脱却）
- [x] S31-12 RAG opcode bridge 実装（`COLLECT/NORMALIZE/INDEX/SEARCH_RAG/CITE_RAG`）
- [x] S31-13 opcode args schema guard（型/必須/範囲）追加
- [x] S31-14 retrieve robustness 強化（fixture/lookup error code分類）
- [x] S31-15 execution budget guard（max_steps/docs/cites）追加

### Phase-4: Runner Operability (S31-16..S31-20)

- [x] S31-16 runner `--resume` 実装（partial artifact から再開）
- [x] S31-17 runner shard 実行（分割実行 + deterministic merge）
- [x] S31-18 quarantine 機能（問題caseを除外して継続実行）
- [x] S31-19 failure digest 生成（`failure_digest.json/md`）
- [x] S31-20 doctor v2（resume/shard/quarantine 成果物整合チェック）

### Phase-5: Quality & Readiness (S31-21..S31-25)

- [x] S31-21 IL acceptance wall v5（S31追加契約の受入壁）
- [x] S31-22 regression safety v2（S22/S23契約の回帰防止）
- [x] S31-23 reliability soak v2（runモード長時間健全性）
- [x] S31-24 policy drift guard（contract/schema/code drift検知）
- [x] S31-25 evidence trend index v6（S31 phase横断可視化）

### Phase-6: DX Finish & Handoff (S31-26..S31-30)

- [x] S31-26 `scripts/ilctl.py` で IL操作を統一サブコマンド化
- [x] S31-27 Makefile ターゲット統一（`make il-*` 体系整理）
- [x] S31-28 runbook v2（quickstart + decision tree + troubleshooting）
- [x] S31-29 S31 closeout generator で Before/After と未解決リスクを固定
- [x] S31-30 S32 handoff pack（開始条件・残課題・優先順）を確定

## Validation Commands

軽量:

- `make ops-now`
- `python3 -m unittest -v tests/test_current_point.py`
- `python3 -m unittest -v tests/test_il_compile.py tests/test_il_validator.py`

中量:

- `make il-thread-smoke`
- `make il-thread-replay-check`
- `make verify-il-thread-v2`
- `make bench-il-compile`

重量（ship前）:

- `make verify-il`
- `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## PR Body Block (S31 template)

```md
### S31-XX <title>
- scope: <what changed>
- acceptance: <which criteria passed>
- commands:
  - `<cmd1>` -> OK
  - `<cmd2>` -> OK
- risks:
  - <residual risk>
- next:
  - S31-YY
```
