# S20-04 TASK: Eval Wall v1 — Mixed Hallucination Hardening

- [ ] 00 Observe: branch/status
  - bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null; echo "BRANCH=$(git rev-parse --abbrev-ref HEAD)"; git status -sb 2>&1'
- [ ] 01 Observe: target files exist
  - bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null; ls -l eval/run_eval.py tests/test_eval_logic.py docs/ops/S20-04_PLAN.md docs/ops/S20-04_TASK.md 2>&1'
- [ ] 02 Edit: eval/run_eval.py（unknown表記ゆれ + mixed hallucination 検出）
  - SKIP: 変更不要なら理由を1行で残す
- [ ] 03 Edit: tests/test_eval_logic.py（期待値を “嘘なし” に整合）
  - SKIP: 変更不要なら理由を1行で残す
- [ ] 04 Light Verify: python test 1本だけ
  - bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null; python3 -m unittest tests.test_eval_logic.TestEvalLogic.test_negative_control_strict 2>&1'
- [ ] 05 Commit: docs+code+test（最小コミット、重いのはまだ回さない）
- [ ] 06 Heavy Gates（最後・nice）
  - bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null; nice -n 10 go test ./... 2>&1'
  - bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null; nice -n 10 go run cmd/reviewpack/main.go submit --mode verify-only 2>&1'
- [ ] 07 PR本文（SOT/Evidence）を .local/handoff に生成
