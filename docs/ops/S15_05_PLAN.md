# S15-05: AI Work v1 — deterministic local AI lane + evidence rails

## Goal
S15-04で固めた hygiene + evidence rails の上で、AI作業（ローカルLLM/RAG/評価）を「壊れず・汚さず・再現できる」形で回せるようにする。

## Non-Goals (Out of scope)
- モデル品質の追求（精度改善・プロンプト芸の沼は後）
- UI/UX強化（見た目・整形）
- ネットワーク依存（オンラインAPI依存は禁止）
- repo汚染の例外追加（許可域を増やさない）

## Hard Invariants
- IF 実行が repo root に新規ファイル/変更を書いた THEN error（`.local/**` と tempdir 以外禁止）
- IF 実行が非決定論（時刻/乱数/順序）に依存 THEN error（seed/順序固定）
- IF 失敗した THEN fail-fast + その場で原因とパスを出す（黙って進まない）
- 証拠は bundle/pack に乗る（“どの入力→どの出力” が辿れる）

## Fixed edit targets (確定パス)
- docs/ops/S15_05_PLAN.md
- docs/ops/S15_05_TASK.md
- （AI作業の実体：既存を優先して編集）
  - src/local_llm.py
  - src/ask.py
  - eval/run_eval.py
  - prompts/system.md
  - prompts/rag.md
  - infra/run-llama-server.sh
  - docs/rules/AI_TEXT_GUARD.md

## Plan (pseudo)
plan:
  IF git status is dirty:
    STOP with error (no implicit cleanup)

  FOR each candidate AI entrypoint in [src/local_llm.py, src/ask.py, eval/run_eval.py]:
    IF file exists:
      select it as primary lane
      break
    ELSE:
      continue
  IF no entrypoint selected:
    error("No AI entrypoint found")

  WHILE implementing:
    enforce deterministic knobs:
      - seed fixed
      - sorted iteration order
      - fixed tempdir prefix OR `.local/ai_runs/**`
      - no timestamps in semantic outputs (logはOK、証拠は固定)
    add evidence capture:
      - record inputs (prompt + config + model id + seed)
      - record outputs (response, metrics)
      - record hash (sha256) for each artifact

    run minimal tests (fast)
    IF tests fail:
      fix smallest cause
      continue
    ELSE:
      break

  run reviewpack submit --mode verify-only
  IF preflight says dirty tree:
    error("Hygiene regression")
  done
