# Maakie Brainlab UI / Ops (SvelteKit)

SvelteKit + TypeScript で実装した Brainlab UI です。

- 通常導線
    - `資料` (`/`): 現在登録されている資料候補を確認する入口
    - `質問` (`/questions`): 答え + 根拠 + 不明表示へ寄せていく入口
    - `根拠` (`/evidence`): 最近の証跡を見る入口
- 内部導線
    - `Ops` (`/ops`): lab / operator / trace 系の退避面
    - `Ops Overview` (`/ops/overview`): 全体状態確認と既存 pipeline 再生成
    - 既存の `Prompt Trace`, `Fine-tune`, `AI Lab`, `Chat + RAG`, `Consensus IL`, `ML Studio`, `RAG Lab`, `LangChain Lab`, `Site Map`, `Site Docs` はここから開く
- UI
    - ヘッダーから `JA / EN` 切替（初期値: `JA`、LocalStorage保存）
- 実行API
    - 既存APIは維持するが、通常ユーザーの main path では前面に出さない

## Why Vite (not RSPack)

2026-02-28 時点で SvelteKit の公式開発サーバー/ビルド基盤は Vite です。
RSPack 直結は公式安定運用ではないため、このMVPは Vite 構成にしています。

## Run

```bash
# terminal A: local model server
cd /Users/takemuramasaki/dev/maakie-brainlab
./infra/run-llama-server.sh /Users/takemuramasaki/brainvault/maakie-brainvault/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
```

```bash
# terminal B: UI
cd ops/dashboard
cp .env.example .env # first time only
export OPENAI_API_BASE=http://127.0.0.1:11434/v1
npm install
npm run dev
```

Default port is fixed to `3033` (`strictPort=true`).

起動後の通常導線は `資料 / 質問 / 根拠` です。運用面は `/ops` から入ってください。

## API Endpoints

- `GET /api/dashboard/overview`
- `GET /api/dashboard/history?limit=200`
- `GET /api/dashboard/evidence?path=docs/evidence/...`
- `GET /api/dashboard/prompt-trace?limit=40`
- `POST /api/dashboard/run` body:

```json
{
	"pipeline": "rag | langchain | ml | quality | operator | all",
	"runDir": "optional, used by operator"
}
```

- `GET /api/dashboard/ai-lab/history?limit=60`
- `POST /api/dashboard/ai-lab/run` body:

```json
{
	"channel": "local-model | mcp | ai-cli | fine-tune | rag-tuning | langchain",
	"prompt": "optional for some channels",
	"commandTemplate": "required for mcp/ai-cli, supports {prompt}",
	"profiles": "optional for fine-tune",
	"seed": 7
}
```

- `GET /api/dashboard/rag-sources`
- `POST /api/dashboard/rag-sources` body:

```json
{
	"name": "S25 RAG Report",
	"path": "docs/evidence/s25-08/rag_tuning_latest.json",
	"tags": "rag,tuning,s25",
	"description": "rag tuning latest report",
	"enabled": true
}
```

- `PATCH /api/dashboard/rag-sources/{id}`
- `DELETE /api/dashboard/rag-sources/{id}`
- `POST /api/dashboard/chat/run` body:

```json
{
	"message": "RAGの改善ポイントを教えて",
	"messages": [{ "role": "user", "content": "前提の質問" }],
	"selectedRagIds": ["source-id-1"]
}
```

- `GET /api/dashboard/fine-tune/history?limit=30`
- `GET /api/dashboard/run-inspector/latest?scope=ai-lab|chat-lab`
- `GET /api/dashboard/consensus/history?limit=30`
- `POST /api/dashboard/consensus/run` body:

```json
{
	"prompt": "shared prompt for all agents",
	"cliCommandTemplate": "echo CLI_AGENT {prompt}",
	"apiBase": "optional openai-compatible base",
	"apiModel": "optional model name",
	"apiKey": "optional key"
}
```

Contract違反 (`WARN`/`FAIL`) は以下に自動記録されます。

- `docs/evidence/dashboard/consensus_contract_latest.json`
- `docs/evidence/dashboard/consensus_contract/consensus_contract_*.json`

Run Inspector の実行トレースは以下に保存されます（JSONLと併存）。

- `.local/obs/dashboard/run_inspector.sqlite3`
    - `runs`
    - `messages`
    - `retrievals`
    - `votes`

## Lint / Format

```bash
npm run lint
npm run lint:fix
npm run format
npm run format:check
```

## Tests

```bash
npm run test:unit
npm run test:e2e
```

## Environment

- Optional: `MAAKIE_REPO_ROOT=/absolute/path/to/maakie-brainlab`
- Optional: `OPENAI_API_BASE=http://127.0.0.1:11434/v1` (local model endpoint)
- Optional: `LOCAL_GGUF_MODEL=Qwen2.5-7B-Instruct`
- Optional: `OPENAI_API_KEY=dummy`
- Default behavior: dashboard process cwd からリポジトリルートを自動検出
- API base は `/v1/chat/completions` と `/chat/completions` を自動フォールバックします。
