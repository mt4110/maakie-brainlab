# docs/ops README

このディレクトリは、**current operator docs** と **historical thread records** が混在しています。
今の判断材料として使う文書は少数に絞ってください。

## 現在の source of truth

読む順番は次です。

1. `AGENTS.override.md`
2. `IL_PIVOT_PRODUCT.md`
3. `AGENTS.md`
4. `README.md`
5. `PRODUCT.md`
6. `docs/il/*` の contract 文書

## このディレクトリで今も読む価値があるもの

- `docs/ops/PR_WORKFLOW.md`
- `docs/ops/CI_REQUIRED_CHECKS.md`
- `docs/ops/IL_THREAD_RUNNER_V2_CONTRACT.md`
- `docs/ops/IL_ENTRY_RUNBOOK.md`
- `docs/ops/MULTIMODEL_POLICY_v1.md`
- `docs/ops/OBS_FORMAT_v1.md`

## archive-only 扱いのもの

次は削除対象ではありませんが、**現在の意思決定には使わない**でください。

- `docs/ops/S*.md`
- closeout / handoff / PLAN / TASK 系の historical thread docs
- 過去の implementation prompt 文書
- `ROADMAP.md` と `STATUS.md` の旧運用前提

## 進捗の置き場所

進捗の source of truth は **PR body** です。
`STATUS.md` は current progress tracker として使いません。

## 最小チェック

Python 系:

```bash
python3 -m unittest discover tests
```

Dashboard 系:

```bash
cd ops/dashboard
npm run check
npm run test:unit
```
