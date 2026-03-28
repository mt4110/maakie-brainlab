<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';

	interface OpsLink {
		href: string;
		title: string;
		noteJa: string;
		noteEn: string;
	}

	interface OpsGroup {
		titleJa: string;
		titleEn: string;
		copyJa: string;
		copyEn: string;
		items: OpsLink[];
	}

	interface InventoryGroup {
		titleJa: string;
		titleEn: string;
		copyJa: string;
		copyEn: string;
		items: string[];
	}

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	const groups: OpsGroup[] = [
		{
			titleJa: '運用の入口',
			titleEn: 'Operator control',
			copyJa: 'overview と既存の再生成操作はここから入れます。',
			copyEn: 'Use this entry point for overview and existing regenerate actions.',
			items: [
				{
					href: '/ops/overview',
					title: 'Ops Overview',
					noteJa: '全体状態の確認と既存 pipeline 再生成',
					noteEn: 'Inspect overall health and trigger existing pipeline regeneration'
				}
			]
		},
		{
			titleJa: '暫定フロー',
			titleEn: 'Transitional flows',
			copyJa: 'Phase 2 へ移し替えるまで残す入口です。',
			copyEn: 'These are temporary entry points until Phase 2 absorbs them.',
			items: [
				{
					href: '/chat-lab',
					title: 'Chat + RAG',
					noteJa: '現行の質問実行と候補ソース管理',
					noteEn: 'Current question execution and source management'
				},
				{
					href: '/history',
					title: 'Evidence History',
					noteJa: '詳細な履歴と比較',
					noteEn: 'Detailed evidence timeline and comparisons'
				}
			]
		},
		{
			titleJa: '運用 / ラボ',
			titleEn: 'Operator and lab',
			copyJa: '通常ユーザーの main path から外した内部面です。',
			copyEn: 'These internal pages are intentionally removed from the main user path.',
			items: [
				{
					href: '/prompt-trace',
					title: 'Prompt Trace',
					noteJa: '生プロンプトと compile 追跡',
					noteEn: 'Raw prompt and compile trace'
				},
				{
					href: '/fine-tune',
					title: 'Fine-tune',
					noteJa: 'prompt loop 実行と履歴',
					noteEn: 'Prompt loop runs and history'
				},
				{
					href: '/ai-lab',
					title: 'AI Lab',
					noteJa: 'ローカルモデル / MCP / CLI 実行',
					noteEn: 'Local model, MCP, and CLI execution'
				},
				{
					href: '/consensus-il',
					title: 'Consensus IL',
					noteJa: '合意形成検証',
					noteEn: 'Consensus validation'
				},
				{
					href: '/ml-studio',
					title: 'ML Studio',
					noteJa: 'ML 実験チュートリアル',
					noteEn: 'ML experiment tutorial'
				},
				{
					href: '/rag-lab',
					title: 'RAG Lab',
					noteJa: 'RAG 調整と検証',
					noteEn: 'RAG tuning and validation'
				},
				{
					href: '/langchain-lab',
					title: 'LangChain Lab',
					noteJa: 'LangChain PoC',
					noteEn: 'LangChain proof of concept'
				}
			]
		},
		{
			titleJa: '案内',
			titleEn: 'Reference',
			copyJa: '内部面の地図と API/保存先の説明です。',
			copyEn: 'Maps and reference docs for the internal surfaces.',
			items: [
				{
					href: '/sitemap',
					title: 'Site Map',
					noteJa: '旧ダッシュボード全体の地図',
					noteEn: 'Map of the legacy dashboard'
				},
				{
					href: '/site-docs',
					title: 'Site Docs',
					noteJa: '画面と API の詳細',
					noteEn: 'Screen and API reference'
				}
			]
		}
	];

	const inventoryGroups: InventoryGroup[] = [
		{
			titleJa: '残す',
			titleEn: 'Keep',
			copyJa: '通常ユーザーの main path として維持する面です。',
			copyEn: 'These surfaces remain the main user path.',
			items: ['/', '/questions', '/evidence', '/ops', '/ops/overview']
		},
		{
			titleJa: 'Ops へ退避',
			titleEn: 'Move behind Ops',
			copyJa: 'いきなり削除せず、まず製品導線から外して隔離する面です。',
			copyEn: 'These stay available, but behind Ops instead of the product front door.',
			items: [
				'/history',
				'/chat-lab',
				'/prompt-trace',
				'/fine-tune',
				'/ai-lab',
				'/consensus-il',
				'/ml-studio',
				'/rag-lab',
				'/langchain-lab'
			]
		},
		{
			titleJa: '削除候補の条件',
			titleEn: 'Deletion candidate criteria',
			copyJa: '次の条件を満たしたときだけ削除判断します。まだ今は消しません。',
			copyEn: 'Delete only after these conditions are met. Do not remove them yet.',
			items: [
				'/ops からも実質使っていない',
				'代替導線ができている',
				'API や test がもう依存していない',
				'最近の作業で誰も触っていない',
				'Site Map / Site Docs のように役割が薄い面から先に見る'
			]
		}
	];

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}
</script>

<div class="surface-stack">
	<section class="hero">
		<article class="panel panel-strong">
			<p class="eyebrow">Ops</p>
			<h1 class="title">
				{tx(
					'通常導線から外した内部面を、ここにまとめました。',
					'Internal surfaces removed from the main path live here.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'PRODUCT.md に合わせて、operator / lab / trace 系は通常ユーザーの main path から外しました。必要なときだけここから入ります。',
					'To align with PRODUCT.md, operator, lab, and trace pages are off the main user path. Enter them only when needed.'
				)}
			</p>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('棚卸し方針', 'Inventory policy')}</p>
			<h2 class="section-title">
				{tx(
					'古い面は、削除より先に「主役かどうか」で分けます。',
					'Before deleting old pages, we sort them by whether they belong on the product path.'
				)}
			</h2>
			<p class="section-copy">
				{tx(
					'不要スクリプトや旧画面は、いきなり消さずに 凍結 → Ops へ退避 → 観察 → 削除判断 の順で扱います。',
					'Old pages and scripts are handled in order: freeze, move behind Ops, observe, then decide on deletion.'
				)}
			</p>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('戻り先', 'Back to main path')}</p>
			<div class="inline-actions">
				<a class="btn-link btn-primary" href="/">{tx('資料へ戻る', 'Back to Documents')}</a>
				<a class="btn-link btn-ghost" href="/questions"
					>{tx('質問へ戻る', 'Back to Questions')}</a
				>
				<a class="btn-link btn-ghost" href="/evidence"
					>{tx('根拠へ戻る', 'Back to Evidence')}</a
				>
			</div>
		</article>
	</section>

	<section class="panel">
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('棚卸し', 'Surface inventory')}</p>
				<h2 class="section-title">
					{tx(
						'残す・退避する・削除候補にする条件を、ここで固定します。',
						'This is where we lock the rules for keep, isolate, and eventual deletion.'
					)}
				</h2>
			</div>
		</div>
		<div class="route-grid">
			{#each inventoryGroups as group}
				<article class="surface-card">
					<p class="eyebrow">{tx(group.titleJa, group.titleEn)}</p>
					<p class="section-copy">{tx(group.copyJa, group.copyEn)}</p>
					<ul class="flat-list">
						{#each group.items as item}
							<li>{item}</li>
						{/each}
					</ul>
				</article>
			{/each}
		</div>
	</section>

	{#each groups as group}
		<section class="panel">
			<div class="section-head">
				<div>
					<p class="eyebrow">{tx(group.titleJa, group.titleEn)}</p>
					<h2 class="section-title">{tx(group.copyJa, group.copyEn)}</h2>
				</div>
			</div>
			<div class="route-grid">
				{#each group.items as item}
					<a class="route-card" href={item.href}>
						<p class="route-title">{item.title}</p>
						<p class="section-copy">{tx(item.noteJa, item.noteEn)}</p>
					</a>
				{/each}
			</div>
		</section>
	{/each}
</div>
