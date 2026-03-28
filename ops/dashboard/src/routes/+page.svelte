<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { RagSourceItem } from '$lib/server/types';

	interface PageData {
		sources: RagSourceItem[];
		sourcesDegraded: boolean;
		sourcesMessageJa: string | null;
		sourcesMessageEn: string | null;
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
			<p class="eyebrow">{tx('はじめての30秒', 'Your first 30 seconds')}</p>
			<h1 class="title">
				{tx(
					'まず見るのは、資料・質問・根拠の 3 つだけです。',
					'Start with only three things: documents, questions, and evidence.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'答えが出ないときは失敗ではありません。資料が足りないか、質問が広すぎる可能性があります。',
					'Not getting an answer is not a failure. The documents may be missing or the question may still be too broad.'
				)}
			</p>
			<ol class="flat-list">
				<li>
					{tx(
						'資料で、今入っている資料を確認する',
						'Use Documents to confirm what is currently loaded'
					)}
				</li>
				<li>
					{tx(
						'質問で、知りたいことをそのまま聞く',
						'Use Questions to ask what you want to know in natural language'
					)}
				</li>
				<li>
					{tx(
						'根拠で、答えの裏付けを確認する',
						'Use Evidence to confirm what supports the answer'
					)}
				</li>
			</ol>
			<p class="section-copy">
				{tx(
					'運用・再生成・実験・追跡は Ops にあります。まずはこの 3 面だけで進めてください。',
					'Operations, regeneration, experiments, and trace views live in Ops. Stay with these three surfaces first.'
				)}
			</p>
			<div class="inline-actions">
				<a class="btn-link btn-primary" href="/questions"
					>{tx('質問へ進む', 'Go to Questions')}</a
				>
				<a class="btn-link btn-ghost" href="/evidence"
					>{tx('根拠を見る', 'Open Evidence')}</a
				>
				<a class="btn-link btn-ghost" href="/ops">{tx('Ops を開く', 'Open Ops')}</a>
			</div>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('資料', 'Documents')}</p>
			<h2 class="section-title">
				{tx(
					'現在の知識ベース候補を確認する画面です。',
					'This is the screen for confirming the current knowledge-base candidates.'
				)}
			</h2>
			<p class="section-copy">
				{tx(
					'ここでは何が登録されているかだけを見ます。答えを得るのは質問、答えの裏付けを見るのは根拠です。',
					'Use this screen only to see what is registered. Questions are for answers, and Evidence is for verification.'
				)}
			</p>
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
						'有効: 質問時の参照候補に入ります。',
						'Enabled: included as a candidate during question answering.'
					)}
				</li>
				<li>
					{tx(
						'パス: 元資料の置き場所です。',
						'Path: where the source document lives.'
					)}
				</li>
				<li>
					{tx(
						'タグ: 資料の分類です。',
						'Tags: how the document is categorized.'
					)}
				</li>
			</ul>
			<p class="section-copy">
				{tx(
					'資料を確認したら、次は質問に進んでください。詳しい追加・編集・再生成は Ops にあります。',
					'After reviewing the documents, continue to Questions. Detailed add/edit/regenerate work stays in Ops.'
				)}
			</p>
			<div class="inline-actions">
				<a class="btn-link btn-primary" href="/questions"
					>{tx('質問へ進む', 'Continue to Questions')}</a
				>
				<a class="btn-link btn-ghost" href="/ops">{tx('詳細管理は Ops', 'Detailed management in Ops')}</a>
			</div>
			{#if data.sourcesDegraded && (data.sourcesMessageJa || data.sourcesMessageEn)}
				<p class="section-copy">{tx(data.sourcesMessageJa ?? '', data.sourcesMessageEn ?? '')}</p>
			{/if}
		</article>
	</section>

	<section class="panel">
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('資料一覧', 'Document list')}</p>
				<h2 class="section-title">
					{tx(
						'現在の知識ベース候補を、名前と経路だけで把握できるようにしました。',
						'The current knowledge-base candidates are visible by name and path.'
					)}
				</h2>
			</div>
			<a class="btn-link btn-ghost" href="/questions"
				>{tx('一覧を見たら質問へ', 'After the list, go to Questions')}</a
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
