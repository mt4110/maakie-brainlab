# Maakie Ops Dashboard (SvelteKit)

SvelteKit + TypeScript で実装した運用ダッシュボードです。

- 主要画面
    - `Overview`: RAG / LangChain / ML / Quality / Operator の最新指標
    - `Evidence History`: `docs/evidence/**/_latest.json` と Contract違反ログの履歴 + JSON比較
    - `Prompt Trace`: `il.compile.prompt.txt` + raw response + compile report
    - `Fine-tune`: prompt loop 実行と履歴
    - `AI Lab`: Local Model / MCP / AI CLI 実行と履歴登録
    - `Chat + RAG`: Chatモード + RAG提案 + サイドメニューでRAGソースCRUD
    - `Consensus IL`: CLI / LOCAL / API 合意形成（contract / guard / evidence / result / time）
    - `ML Studio`: 手順とTipsつきチュートリアル
    - `RAG Lab`: RAG調整実行と検証
    - `LangChain Lab`: PoC実行とrollback運用ガイド
    - `Site Map`: 画面機能の一覧と最短導線
    - `Site Docs`: 画面/API/保存先/運用コマンドの詳細説明
- UI
    - ヘッダーから `JA / EN` 切替（初期値: `JA`、LocalStorage保存）
    - 既存主要ページ本文も `JA / EN` 切替に対応
- 実行API
    - RAG tuning, LangChain PoC, ML experiment, quality burndown, operator export

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
# terminal B: dashboard
cd ops/dashboard
cp .env.example .env # first time only
export OPENAI_API_BASE=http://127.0.0.1:11434/v1
npm install
npm run dev
```

Default port is fixed to `3033` (`strictPort=true`).

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
