# maakie-brainlab

**maakie-brainlab** は、自然言語の目的を **IL plan** に正規化し、step 実行・evidence・artifact・next action・resume まで追えるローカル研究コックピットです。

この branch の北極星 surface は **`/ops/agent`** です。
現時点の operator shell は `/ops` を使いつつ、専用 cockpit を `/ops/agent` へ寄せていきます。
`/`, `/questions`, `/evidence` は legacy/public track として repo に残しますが、この branch では **maintenance-only** として扱います。

## 今の方向性

この line で固定したい loop は次です。

**Goal -> Normalize -> IL Plan -> Approve -> Execute -> Evidence -> Artifact -> Next Action -> Resume**

重視しているのは次の 4 点です。

- deterministic state
- typed blocked reason
- evidence linkage
- pause / resume

派手さより、**再実行できること** と **後から検証できること** を優先します。

## まず読むもの

迷ったら、次の順で読んでください。

1. `AGENTS.override.md`
2. `IL_PIVOT_PRODUCT.md`
3. `AGENTS.md`
4. `PRODUCT.md`
5. `docs/ops/README.md`
6. `docs/il/IL_CONTRACT_v1.md` と関連 contract

補足:

- `PRODUCT.md` は legacy/public track の定義です
- `IL_PIVOT_PRODUCT.md` がこの branch の研究 north star です
- `docs/ops/S*.md` は historical records であり、現在の source of truth ではありません

## Quickstart

### 1. モデル backend を決める

OpenAI-compatible runtime を使う場合:

```bash
export LOCAL_MODEL_BACKEND=openai_compat
export OPENAI_API_BASE=http://127.0.0.1:11434/v1
export OPENAI_API_KEY=dummy
```

`gemma-lab` を使う場合:

```bash
export LOCAL_MODEL_BACKEND=gemma_lab
export GEMMA_MODEL_ID=google/gemma-4-E2B-it
```

必要なら次も上書きできます。

- `GEMMA_LAB_ROOT`
- `GEMMA_LAB_PYTHON`

### 2. Dashboard を起動する

```bash
cd ops/dashboard
cp .env.example .env
npm install
npm run dev
```

まずはブラウザで `http://127.0.0.1:3033/ops` を開いてください。

runtime の接続確認だけ先に見たい場合は `http://127.0.0.1:3033/rag-lab` も使えます。
専用 cockpit route が入っている checkout では `http://127.0.0.1:3033/ops/agent` を使います。

## この branch で作っているもの

主に作っているのは次です。

- `/ops/agent` の goal input と recent runs
- `/ops/agent/[id]` の plan / steps / evidence / artifacts / blocked reason / next action
- IL compile / execute の deterministic core
- model/backend switching を UI 意味論から分離した runtime contract

## いま主戦場ではないもの

この branch では、次に main effort を置きません。

- `/`, `/questions`, `/evidence` の public Q&A polish
- crawler infrastructure
- web-scale ingestion
- flashy autonomy
- 新しい public-facing product surface

## docs の整理方針

混乱を避けるため、文書は次のルールで読みます。

- 現在の方向性: `AGENTS.override.md` と `IL_PIVOT_PRODUCT.md`
- legacy/public track: `PRODUCT.md`
- 実装の入口: `README.md` と `docs/ops/README.md`
- runtime / schema: `docs/il/*`
- historical thread docs: `docs/ops/S*.md` は archive-only
- progress: `STATUS.md` ではなく PR body

## よく使う確認コマンド

```bash
python3 -m unittest -v tests/test_il_compile.py tests/test_il_thread_runner_v2.py
cd ops/dashboard && npm run check && npm run test:unit
```

PR 作成や更新の前には、repo root で `ci-self up --ref "$(git branch --show-current)"` を実行します。

## ライセンス

本プロジェクトは **商用ライセンス (Commercial License)** の下で提供されています。
無断での複製、改変、再配布は禁止されています。
