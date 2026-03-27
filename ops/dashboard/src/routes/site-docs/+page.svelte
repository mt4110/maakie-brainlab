<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	interface DocRow {
		label: string;
		value: string;
	}

	const endpointRows = $derived(
		[
			{
				path: 'GET /api/dashboard/overview',
				purposeJa: '概要の集計取得',
				purposeEn: 'Fetch overview aggregation'
			},
			{
				path: 'GET /api/dashboard/history',
				purposeJa: 'Evidence履歴取得',
				purposeEn: 'Fetch evidence history'
			},
			{
				path: 'GET /api/dashboard/evidence?path=...',
				purposeJa: 'Evidence JSON単体取得',
				purposeEn: 'Fetch a single evidence JSON by path'
			},
			{
				path: 'GET /api/dashboard/prompt-trace',
				purposeJa: 'プロンプト追跡履歴取得',
				purposeEn: 'Fetch prompt trace history'
			},
			{
				path: 'POST /api/dashboard/run',
				purposeJa: 'パイプライン実行',
				purposeEn: 'Run pipelines'
			},
			{
				path: 'POST /api/dashboard/ai-lab/run',
				purposeJa: 'AI Lab 実行',
				purposeEn: 'Run AI Lab command'
			},
			{
				path: 'GET /api/dashboard/rag-sources?q=&page=&pageSize=',
				purposeJa: 'RAGソース一覧取得（検索/ページング）',
				purposeEn: 'Fetch RAG source list (search/pagination)'
			},
			{
				path: 'POST /api/dashboard/rag-sources',
				purposeJa: 'RAGソース作成',
				purposeEn: 'Create RAG source'
			},
			{
				path: 'PATCH /api/dashboard/rag-sources/{id}',
				purposeJa: 'RAGソース更新',
				purposeEn: 'Update RAG source'
			},
			{
				path: 'DELETE /api/dashboard/rag-sources/{id}',
				purposeJa: 'RAGソース削除',
				purposeEn: 'Delete RAG source'
			},
			{
				path: 'POST /api/dashboard/chat/run',
				purposeJa: 'Chatモード実行（RAG提案付き）',
				purposeEn: 'Run chat mode with RAG suggestions'
			},
			{
				path: 'GET /api/dashboard/ai-lab/history',
				purposeJa: 'AI Lab 履歴',
				purposeEn: 'Fetch AI Lab history'
			},
			{
				path: 'GET /api/dashboard/run-inspector/latest?scope=ai-lab|chat-lab',
				purposeJa: 'Run Inspector の最新実行を取得',
				purposeEn: 'Fetch latest Run Inspector record'
			},
			{
				path: 'POST /api/dashboard/consensus/run',
				purposeJa: 'コンセンサス実行',
				purposeEn: 'Run consensus job'
			},
			{
				path: 'GET /api/dashboard/consensus/history',
				purposeJa: 'コンセンサス履歴',
				purposeEn: 'Fetch consensus history'
			}
		].map((row) => ({
			label: row.path,
			value: localeState.value === 'ja' ? row.purposeJa : row.purposeEn
		})) satisfies DocRow[]
	);

	const fileRows = $derived(
		[
			{
				path: '.local/obs/dashboard/ai_lab_runs.jsonl',
				noteJa: 'AI Labの実行履歴',
				noteEn: 'AI Lab run history'
			},
			{
				path: '.local/obs/dashboard/consensus_runs.jsonl',
				noteJa: 'Consensus実行履歴',
				noteEn: 'Consensus run history'
			},
			{
				path: '.local/obs/dashboard/rag_sources.sqlite3',
				noteJa: 'RAGソース設定DB（CRUD対象）',
				noteEn: 'RAG source settings DB (CRUD target)'
			},
			{
				path: '.local/obs/dashboard/chat_runs.jsonl',
				noteJa: 'Chatモード実行ログ',
				noteEn: 'Chat mode run log'
			},
			{
				path: '.local/obs/dashboard/run_inspector.sqlite3',
				noteJa: 'Run Inspector DB（runs/messages/retrievals/votes）',
				noteEn: 'Run Inspector DB (runs/messages/retrievals/votes)'
			},
			{
				path: 'docs/evidence/dashboard/consensus_contract_latest.json',
				noteJa: '最新のContract違反ログ',
				noteEn: 'Latest contract-violation evidence'
			},
			{
				path: 'docs/evidence/dashboard/consensus_contract/*.json',
				noteJa: 'Contract違反の時系列ログ',
				noteEn: 'Time-series contract-violation evidence logs'
			}
		].map((row) => ({
			label: row.path,
			value: localeState.value === 'ja' ? row.noteJa : row.noteEn
		})) satisfies DocRow[]
	);

	const commandRows = $derived(
		[
			{ cmd: 'npm run dev', ja: '開発サーバー起動 (3033)', en: 'Start dev server (3033)' },
			{ cmd: 'npm run lint', ja: 'ESLint 実行', en: 'Run ESLint' },
			{ cmd: 'npm run check', ja: 'Svelte/TS チェック', en: 'Run Svelte/TS checks' },
			{ cmd: 'npm run build', ja: '本番ビルド確認', en: 'Build production bundle' },
			{ cmd: 'npm run test:unit', ja: 'Vitest 単体テスト', en: 'Run Vitest unit tests' },
			{ cmd: 'npm run test:e2e', ja: 'Cypress E2E テスト', en: 'Run Cypress E2E tests' }
		].map((row) => ({
			label: row.cmd,
			value: localeState.value === 'ja' ? row.ja : row.en
		})) satisfies DocRow[]
	);
</script>

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">Site Docs</p>
	<h1 class="title">{tx('サイトドキュメント', 'Site Documentation')}</h1>
	<p class="muted">
		{tx(
			'画面、API、証拠ファイル、運用コマンドをまとめて参照できるページです。',
			'Single reference for pages, APIs, evidence files, and operating commands.'
		)}
	</p>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Flow</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('推奨の使い方', 'Recommended Flow')}</h2>
	<div class="prompt-list">
		<div class="snippet">
			{tx(
				'1) Chat + RAG で相談しつつ候補ソース確認 → 2) AI ラボやコンセンサス IL で実行検証 → 3) エビデンス履歴で差分比較',
				'1) Use Chat + RAG to discuss and inspect candidate sources -> 2) Validate runs in AI Lab or Consensus IL -> 3) Compare artifacts in Evidence History'
			)}
		</div>
		<div class="snippet">
			{tx(
				'品質確認は Overview で全体ステータスを見て、必要に応じて個別ラボへ戻る流れが最短です。',
				'For quality checks, read global status in Overview and jump back to each lab as needed.'
			)}
		</div>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Endpoints</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('主要API', 'Core APIs')}</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead>
				<tr>
					<th>{tx('エンドポイント', 'Endpoint')}</th>
					<th>{tx('用途', 'Purpose')}</th>
				</tr>
			</thead>
			<tbody>
				{#each endpointRows as row}
					<tr>
						<td class="path">{row.label}</td>
						<td>{row.value}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Evidence</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('保存ファイル', 'Stored Files')}</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead>
				<tr>
					<th>{tx('パス', 'Path')}</th>
					<th>{tx('説明', 'Description')}</th>
				</tr>
			</thead>
			<tbody>
				{#each fileRows as row}
					<tr>
						<td class="path">{row.label}</td>
						<td>{row.value}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<section class="panel">
	<p class="eyebrow">Commands</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('運用コマンド', 'Ops Commands')}</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead>
				<tr>
					<th>{tx('コマンド', 'Command')}</th>
					<th>{tx('説明', 'Description')}</th>
				</tr>
			</thead>
			<tbody>
				{#each commandRows as row}
					<tr>
						<td class="path">{row.label}</td>
						<td>{row.value}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
