# S32-01-S32-10 THREAD v1 PLAN — IL Scale and Quality Uplift

Last Updated: 2026-02-28

## Goal

- S31で追加した IL UX/runner 拡張を実運用スケールへ拡張し、fixture依存から実データ寄り検証へ進める。

## Start Conditions

- `docs/evidence/s31-29/closeout_latest.json` が存在する。
- `docs/evidence/s31-30/handoff_latest.json` が存在する。
- `make verify-il` が green。

## Candidate Phases

1. S32-01: RAG retrieval quality uplift (non-fixture corpus)
2. S32-02: compile prompt profile auto-selection
3. S32-03: runner shard orchestrator automation
4. S32-04: failure digest classifier v2
5. S32-05: operator dashboard JSON export
6. S32-06: latency budget/SLO guard
7. S32-07: acceptance wall v6
8. S32-08: policy drift guard v2
9. S32-09: closeout generator v2
10. S32-10: S33 handoff pack

## Non-negotiables

- Ritual `22-16-22-99` を継続。
- milestone checks は non-blocking を維持。
- 進捗 SOT は TASK + PR body（`STATUS.md` 非依存）。
