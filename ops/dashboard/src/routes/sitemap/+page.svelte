<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	interface SitemapEntry {
		href: string;
		title: string;
		summary: string;
		points: string[];
	}

	const entries = $derived(
		localeState.value === 'ja'
			? ([
					{
						href: '/',
						title: '概要',
						summary: '全体ヘルスと主要パイプラインの最新状態を確認します。',
						points: [
							'PASS/WARN/FAIL を一画面で把握',
							'主要パイプラインをワンクリック実行'
						]
					},
					{
						href: '/ai-lab',
						title: 'AI ラボ',
						summary: 'ローカルモデル・MCP・AI CLI を試行し、結果を履歴に残します。',
						points: ['プロンプト入力で実行', 'コマンドテンプレート実行に対応']
					},
					{
						href: '/chat-lab',
						title: 'Chat + RAG',
						summary: 'チャットをしながら、関連するRAG候補の提案を受けられます。',
						points: ['サイドメニューでRAGソースCRUD', '会話文脈に合わせてRAG候補を表示']
					},
					{
						href: '/consensus-il',
						title: 'コンセンサス IL',
						summary: 'CLI / LOCAL / API を同時実行し、合意を監査可能な形で記録します。',
						points: [
							'contract / guard / evidence / result / time を表示',
							'WARN/FAIL は証拠JSONへ自動保存'
						]
					},
					{
						href: '/history',
						title: 'エビデンス履歴',
						summary: 'Evidence JSON の履歴確認と2件比較ができます。',
						points: ['検索・ステータス絞り込み', '任意2件のJSONを並列比較']
					},
					{
						href: '/prompt-trace',
						title: 'プロンプト追跡',
						summary: 'コンパイル時プロンプトと応答をトレースします。',
						points: ['prompt/raw response/report を追跡', '最近の実行を時系列で確認']
					},
					{
						href: '/fine-tune',
						title: 'ファインチューン',
						summary: 'プロンプト最適化ループの実行履歴を確認します。',
						points: ['best profile を追跡', 'スコア変化を監視']
					},
					{
						href: '/ml-studio',
						title: 'ML スタジオ',
						summary: '軽量MLの実験手順とTipsを確認します。',
						points: ['再ランキング/分類の導入手順', '実運用向けの注意点を整理']
					},
					{
						href: '/rag-lab',
						title: 'RAG ラボ',
						summary: 'RAG調整の現状と改善ポイントを扱います。',
						points: ['指標と調整ポイントを併読', '調整実行との往復がしやすい']
					},
					{
						href: '/langchain-lab',
						title: 'LangChain ラボ',
						summary: 'LangChain PoC と運用上のガイドを確認します。',
						points: ['PoC実行結果を確認', 'ロールバック観点を整理']
					},
					{
						href: '/site-docs',
						title: 'サイトドキュメント',
						summary: '画面/API/ファイル構成の詳細説明ページです。',
						points: ['導入手順を網羅', '運用の参照先を集約']
					}
				] satisfies SitemapEntry[])
			: ([
					{
						href: '/',
						title: 'Overview',
						summary: 'Check overall health and latest status of key pipelines.',
						points: [
							'Single-pane PASS/WARN/FAIL visibility',
							'One-click pipeline execution'
						]
					},
					{
						href: '/ai-lab',
						title: 'AI Lab',
						summary: 'Run Local Model, MCP, and AI CLI flows and keep run history.',
						points: ['Prompt-driven execution', 'Template-based command execution']
					},
					{
						href: '/chat-lab',
						title: 'Chat + RAG',
						summary: 'Chat naturally while receiving relevant RAG source suggestions.',
						points: [
							'Sidebar CRUD for RAG sources',
							'Context-aware RAG recommendations per chat turn'
						]
					},
					{
						href: '/consensus-il',
						title: 'Consensus IL',
						summary:
							'Execute CLI / LOCAL / API together and store auditable consensus results.',
						points: [
							'Shows contract/guard/evidence/result/time',
							'Auto-saves WARN/FAIL evidence JSON'
						]
					},
					{
						href: '/history',
						title: 'Evidence History',
						summary: 'Browse Evidence JSON history and compare two items directly.',
						points: ['Search + status filtering', 'Side-by-side JSON comparison']
					},
					{
						href: '/prompt-trace',
						title: 'Prompt Trace',
						summary: 'Trace compile-time prompts and responses.',
						points: ['Track prompt/raw response/report', 'Review latest traces by time']
					},
					{
						href: '/fine-tune',
						title: 'Fine-tune',
						summary: 'Inspect prompt optimization loop execution history.',
						points: ['Track best profile', 'Monitor score shifts']
					},
					{
						href: '/ml-studio',
						title: 'ML Studio',
						summary: 'Learn lightweight ML experiment steps and tips.',
						points: [
							'Rerank/classification setup guidance',
							'Operational caveats included'
						]
					},
					{
						href: '/rag-lab',
						title: 'RAG Lab',
						summary: 'Tune and inspect RAG state with practical hints.',
						points: [
							'Read metrics and tuning levers together',
							'Fast iterate on adjustments'
						]
					},
					{
						href: '/langchain-lab',
						title: 'LangChain Lab',
						summary: 'Check LangChain PoC and operation notes.',
						points: ['Review PoC run outcomes', 'Keep rollback guidance visible']
					},
					{
						href: '/site-docs',
						title: 'Site Docs',
						summary: 'Detailed page for screens, APIs, and file structures.',
						points: ['Full onboarding reference', 'Centralized operational guides']
					}
				] satisfies SitemapEntry[])
	);

	const pageTitle = $derived(localeState.value === 'ja' ? 'サイトマップ' : 'Site Map');
	const pageSummary = $derived(
		localeState.value === 'ja'
			? '「どこで何ができるか」を短時間で把握できる一覧です。'
			: 'Quick map of where to do what in this dashboard.'
	);
	const quickGuideTitle = $derived(localeState.value === 'ja' ? '最短導線' : 'Quick Routes');
	const quickGuideItems = $derived(
		localeState.value === 'ja'
			? [
					'普通に実行したい: AI ラボ',
					'チャットしながらRAGを使いたい: Chat + RAG',
					'複数AIで合意を取りたい: コンセンサス IL',
					'証拠を追跡したい: エビデンス履歴 + プロンプト追跡',
					'全体健全性を見たい: 概要'
				]
			: [
					'Run plain interactions: AI Lab',
					'Chat with RAG suggestions: Chat + RAG',
					'Get multi-agent consensus: Consensus IL',
					'Track evidence: Evidence History + Prompt Trace',
					'Monitor health: Overview'
				]
	);
</script>

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">Sitemap</p>
	<h1 class="title">{pageTitle}</h1>
	<p class="muted">{pageSummary}</p>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Quick Guide</p>
	<h2 class="title" style="font-size: 1.35rem;">{quickGuideTitle}</h2>
	<div class="prompt-list">
		{#each quickGuideItems as item}
			<div class="snippet">{item}</div>
		{/each}
	</div>
</section>

<section class="panel">
	<p class="eyebrow">Pages</p>
	<h2 class="title" style="font-size: 1.35rem;">
		{localeState.value === 'ja' ? '機能一覧' : 'Capability Index'}
	</h2>
	<div class="card-grid" style="margin-top: 12px;">
		{#each entries as entry}
			<a class="panel pipeline-card" href={entry.href}>
				<h3 class="pipeline-title">{entry.title}</h3>
				<p class="muted" style="margin-top: 0;">{entry.summary}</p>
				{#each entry.points as point}
					<div class="metric-row">
						<span class="metric-label">{point}</span>
						<span class="metric-value">-</span>
					</div>
				{/each}
				<div class="path">{entry.href}</div>
			</a>
		{/each}
	</div>
</section>
