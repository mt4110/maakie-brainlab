# S23-04 PLAN — Compile→Entry Thread Runner v2
Last Updated: 2026-02-26

## Goal
- `compile` と `il_entry` を 1 本のスレッド実行導線に統合し、`validate-only/run` の実行契約を固定する。

## Why Now
- S23-03 で compile 単体品質は確立したが、実運用は「compile -> il_entry」を手でつないでいる。
- `V2` 系の評価運用（`docs/evidence/EVAL_WALL_V2.md`）と同じ mode 契約で、再現可能な e2e 実行面を先に固定する必要がある。

## Acceptance Criteria
- `docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md` を作成し、以下を定義する:
  - case input schema（request + optional constraints + fixture pointers）
  - mode contract（`validate-only` / `run`）
  - fail-closed policy（compile失敗時は entry 実行禁止）
  - observability artifacts（cases / summary / per-case compile+entry artifacts）
  - determinism evidence（同一入力・同一設定で `cases.jsonl` sha256 一致）
- `scripts/il_thread_runner_v2.py` を追加し、`--cases --mode --out` の最小I/Fで動作する。
- `tests/test_il_thread_runner_v2.py` を追加し、以下を回帰防止する:
  - `validate-only` では executor を呼ばない
  - `run` では compile成功ケースのみ entry 実行
  - compile失敗ケースは structured error を保持して fail-closed
- `make verify-il` から呼べる軽量 smoke (`scripts/il_thread_runner_v2_smoke.py`) を追加する。

## Impacted Files
- `docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md` (new)
- `docs/ops/S23-04_PLAN.md`
- `docs/ops/S23-04_TASK.md` (new)
- `scripts/il_thread_runner_v2.py` (new)
- `scripts/il_thread_runner_v2_smoke.py` (new)
- `tests/test_il_thread_runner_v2.py` (new)
- `Makefile`

## Design (v1)
- 標準I/F:
  - `python3 scripts/il_thread_runner_v2.py --cases <jsonl> --mode <validate-only|run> --out <dir> [--provider ... --model ... --prompt-profile ... --seed ...]`
- caseごとに `compile` を実行し、`run` モードかつ compile成功時のみ `il_entry` を実行する。
- `validate-only` は `compile` と構造検証までで止め、executor 実行を禁止する。
- `--out` 配下に `cases.jsonl` / `summary.json` / `cases/<id>/...` を出し、すべて監査可能にする。
- summary は最低でも `compile_ok_count` / `entry_ok_count` / `error_count` / `mode` / `provider` / `seed` を含む。

## Non-Goals
- ANSWER opcode の高品質化
- LocalLLMモデル選定の最適化
- 重量級 eval wall の再実行（本フェーズは lightweight smoke まで）
