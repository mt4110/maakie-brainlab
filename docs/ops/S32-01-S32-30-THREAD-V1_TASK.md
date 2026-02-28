# S32-01-S32-30 THREAD v1 TASK — IL Scale, Quality, and Daily Usability

Last Updated: 2026-02-28

## Progress

- S32-01-S32-30 v1: 67% (S32-01..S32-20 implemented and tested)

## Current Facts

- ブランチは `ops/S32-01-S32-30` を使用。
- 進捗 SOT はこの TASK + PR body（`docs/ops/STATUS.md` は使わない）。
- 実装プロンプトは `docs/ops/S32-01-S32-30-THREAD-V1_PROMPTS.md` を参照。

## Ritual 22-16-22-99

- PLAN: `docs/ops/S32-01-S32-30-THREAD-V1_PLAN.md` で受入条件と依存を固定
- DO: 依存順で最小実装
- CHECK: 軽量 -> 中量 -> 重量 gate
- SHIP: test command/result を PR body に固定

## Checklist

### Phase-1: Retrieval Realism (S32-01..S32-05)

- [x] S32-01 `COLLECT` の non-fixture source（`file_jsonl` / `rss`）対応
- [x] S32-02 retrieval ranking v2（deterministic score + tie-break）
- [x] S32-03 cite provenance v2（snippet/hash/source_path）
- [x] S32-04 corpus policy filter（denylist/lang/size）
- [x] S32-05 retrieval eval wall v1（non-fixture corpus品質壁）

### Phase-2: Compile Reliability (S32-06..S32-10)

- [x] S32-06 compile prompt profile auto-selection
- [x] S32-07 compile confidence contract（confidence/rationale）
- [x] S32-08 compile parse repair guard v3（bounded repair）
- [x] S32-09 prompt loop dataset v2（golden case 拡張）
- [x] S32-10 compile doctor v2（compile起因障害の診断拡張）

### Phase-3: Runner Scale & Observability (S32-11..S32-15)

- [x] S32-11 shard orchestrator v1（分散実行統括CLI）
- [x] S32-12 artifact lease/lock guard（衝突回避）
- [x] S32-13 retry policy matrix（error code別制御）
- [x] S32-14 failure digest classifier v2（root-cause class）
- [x] S32-15 operator dashboard export（JSON出力）

### Phase-4: Quality Gates vNext (S32-16..S32-20)

- [x] S32-16 latency budget/SLO guard
- [x] S32-17 acceptance wall v6（S32契約受入）
- [x] S32-18 policy drift guard v2
- [x] S32-19 reliability soak v3（non-fixture + shard運用）
- [x] S32-20 evidence trend index v7

### Phase-5: IL UX vNext (S32-21..S32-25)

- [ ] S32-21 IL opcode catalog generator
- [ ] S32-22 `ilctl` scenario commands（`quickstart/triage`）
- [ ] S32-23 runbook v3（decision playbooks）
- [ ] S32-24 workspace init v2 templates（domain別雛形）
- [ ] S32-25 doctor v3 with fix hints

### Phase-6: Release and Handoff (S32-26..S32-30)

- [ ] S32-26 regression safety v3（S22/S23/S31/S32 回帰監査）
- [ ] S32-27 release readiness v2（go/no-go 統合判定）
- [ ] S32-28 closeout generator v2
- [ ] S32-29 S33 backlog seed pack
- [ ] S32-30 S33 handoff pack

## Validation Commands

軽量:

- `make ops-now`
- `python3 -m unittest -v tests/test_il_compile.py tests/test_il_validator.py`
- `python3 -m unittest -v tests/test_s32_<target>.py`

中量:

- `make il-thread-smoke`
- `make il-thread-replay-check`
- `make verify-il-thread-v2`
- `make bench-il-compile`

重量（ship前）:

- `make verify-il`
- `source /path/to/your/nix/profile.d/nix-daemon.sh`
- `ci-self up --ref "$(git branch --show-current)"`

## PR Body Block (S32 template)

```md
### S32-XX <title>
- scope: <what changed>
- acceptance: <which criteria passed>
- commands:
  - `<cmd1>` -> OK
  - `<cmd2>` -> OK
- risks:
  - <residual risk>
- next:
  - S32-YY
```
