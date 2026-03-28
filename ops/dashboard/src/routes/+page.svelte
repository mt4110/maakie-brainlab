<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { RagSourceItem } from '$lib/server/types';

	interface PageData {
		sources: RagSourceItem[];
		sourcesDegraded: boolean;
		sourcesMessage: string | null;
	}

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	let { data }: { data: PageData } = $props();

	const enabledCount = $derived(data.sources.filter((item) => item.enabled).length);
	const latestUpdatedAt = $derived(data.sources[0]?.updatedAt ?? null);

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string | null): string {
		if (!isoLike) {
			return tx('未登録', 'Not available');
		}
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function sourceStatusClass(item: RagSourceItem): string {
		return item.enabled ? 'status-pill status-pass' : 'status-pill status-skip';
	}
</script>

<div class="surface-stack">
	<section class="hero">
		<article class="panel panel-strong">
			<p class="eyebrow">{tx('資料', 'Documents')}</p>
			<h1 class="title">
				{tx(
					'通常導線を、今使う資料に戻しました。',
					'The main path is back to the documents you actually use.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'Phase 1 では表面を削り、資料・質問・根拠の3面だけを前に出します。実験系や operator 面は Ops に退避しました。',
					'Phase 1 trims the surface back to three user-facing views: documents, questions, and evidence. Experimental and operator pages are now tucked behind Ops.'
				)}
			</p>
			<div class="inline-actions">
				<a class="btn-link btn-primary" href="/questions"
					>{tx('質問面を見る', 'Open Questions')}</a
				>
				<a class="btn-link btn-ghost" href="/ops">{tx('Ops を開く', 'Open Ops')}</a>
			</div>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('現在の見え方', 'Current surface')}</p>
			<div class="surface-meta">
				<div class="meta-card">
					<p class="meta-label">{tx('登録済み資料', 'Registered documents')}</p>
					<p class="meta-value">{data.sources.length}</p>
				</div>
				<div class="meta-card">
					<p class="meta-label">{tx('有効な資料', 'Enabled documents')}</p>
					<p class="meta-value">{enabledCount}</p>
				</div>
				<div class="meta-card">
					<p class="meta-label">{tx('最終更新', 'Last updated')}</p>
					<p class="meta-copy">{dt(latestUpdatedAt)}</p>
				</div>
			</div>
			<ul class="flat-list">
				<li>
					{tx(
						'この面では登録済み資料を全件表示します。',
						'This surface shows the full registered document list.'
					)}
				</li>
				<li>
					{tx(
						'資料追加や再インデックスの本実装は Phase 2 でここへ寄せます。',
						'Document add/reindex actions will move here in Phase 2.'
					)}
				</li>
			</ul>
			{#if data.sourcesDegraded && data.sourcesMessage}
				<p class="section-copy">{data.sourcesMessage}</p>
			{/if}
		</article>
	</section>

	<section class="panel">
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('登録済み資料', 'Registered documents')}</p>
				<h2 class="section-title">
					{tx(
						'現在の知識ベース候補を、名前と経路だけで把握できるようにしました。',
						'The current knowledge-base candidates are visible by name and path.'
					)}
				</h2>
			</div>
			<a class="btn-link btn-ghost" href="/ops"
				>{tx('詳細管理は Ops', 'Detailed management in Ops')}</a
			>
		</div>

		{#if data.sources.length > 0}
			<div class="card-grid">
				{#each data.sources as item}
					<article class="panel surface-card">
						<div class="pipeline-head">
							<h3 class="pipeline-title">{item.name}</h3>
							<span class={sourceStatusClass(item)}>
								{item.enabled ? tx('有効', 'Enabled') : tx('停止中', 'Disabled')}
							</span>
						</div>
						{#if item.description}
							<p class="section-copy">{item.description}</p>
						{/if}
						<div class="meta-pair">
							<p class="meta-label">{tx('パス', 'Path')}</p>
							<p class="path">{item.path || tx('未設定', 'Not set')}</p>
						</div>
						<div class="meta-pair">
							<p class="meta-label">{tx('タグ', 'Tags')}</p>
							<p class="meta-copy">
								{item.tags.length > 0 ? item.tags.join(', ') : tx('なし', 'None')}
							</p>
						</div>
						<div class="meta-pair">
							<p class="meta-label">{tx('更新', 'Updated')}</p>
							<p class="meta-copy">{dt(item.updatedAt)}</p>
						</div>
					</article>
				{/each}
			</div>
		{:else}
			<div class="empty-state">
				<p class="section-title">
					{tx('まだ資料が登録されていません。', 'No documents are registered yet.')}
				</p>
				<p class="section-copy">
					{tx(
						'Phase 1 では表面整理を優先しています。暫定の登録導線は Ops 側に残しています。',
						'Phase 1 prioritizes surface simplification. Transitional registration controls remain in Ops for now.'
					)}
				</p>
			</div>
		{/if}
	</section>
</div>
