# maakie-brainlab

**maakie-brainlab** is a local research cockpit that turns natural-language goals into **IL plans**, step execution, evidence, artifacts, next actions, and resumable state.

The north-star surface on this branch is **`/ops/agent`**.
Today, the operator shell still starts from `/ops`, while the dedicated cockpit is being pulled into `/ops/agent`.
The public Q&A path (`/`, `/questions`, `/evidence`) still exists in the repo, but it is treated as a legacy/public track and is not the main optimization target here.

## Current direction

The core loop on this branch is:

**Goal -> Normalize -> IL Plan -> Approve -> Execute -> Evidence -> Artifact -> Next Action -> Resume**

The priority is:

- deterministic state
- typed blocked reasons
- evidence linkage
- pause and resume

## Read These First

1. `AGENTS.override.md`
2. `IL_PIVOT_PRODUCT.md`
3. `AGENTS.md`
4. `PRODUCT.md`
5. `docs/ops/README.md`
6. `docs/il/IL_CONTRACT_v1.md` and related contracts

Notes:

- `PRODUCT.md` defines the legacy/public product track
- `IL_PIVOT_PRODUCT.md` is the active research north star on this branch
- `docs/ops/S*.md` files are historical records, not current source of truth

## Quickstart

Choose a local model backend first.

OpenAI-compatible:

```bash
export LOCAL_MODEL_BACKEND=openai_compat
export OPENAI_API_BASE=http://127.0.0.1:11434/v1
export OPENAI_API_KEY=dummy
```

`gemma-lab`:

```bash
export LOCAL_MODEL_BACKEND=gemma_lab
export GEMMA_MODEL_ID=google/gemma-4-E2B-it
```

Start the dashboard:

```bash
cd ops/dashboard
cp .env.example .env
npm install
npm run dev
```

Open `http://127.0.0.1:3033/ops` first.

If you want to smoke-test the local model runtime first, `http://127.0.0.1:3033/rag-lab` is still useful as an operator check surface.
If your checkout already includes the dedicated cockpit route, use `http://127.0.0.1:3033/ops/agent`.

## What This Branch Is Building

- an operator/research cockpit under `/ops/agent`
- deterministic IL compile and execution contracts
- evidence and artifact attachment per step
- typed blocked reasons and resume flow
- model/backend switching that does not change UI semantics

## What Is Not The Main Focus Here

- polishing the public Q&A path
- crawler infrastructure
- web-scale ingestion
- flashy autonomy
- a new public-facing product surface

## Documentation Hygiene

To keep the repo readable:

- current direction lives in `AGENTS.override.md` and `IL_PIVOT_PRODUCT.md`
- legacy/public product definition lives in `PRODUCT.md`
- implementation entrypoints live in `README.md` and `docs/ops/README.md`
- runtime contracts live in `docs/il/*`
- historical thread docs under `docs/ops/S*.md` are archive-only
- progress belongs in the PR body, not `STATUS.md`

## License

This project is licensed under a **Commercial License**. Unauthorized copying, modification, or redistribution is prohibited.
