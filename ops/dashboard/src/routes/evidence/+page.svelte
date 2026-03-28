<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { EvidenceHistoryItem } from '$lib/server/types';

	interface PageData {
		history: EvidenceHistoryItem[];
	}

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	let { data }: { data: PageData } = $props();

	const recentPassCount = $derived(
		data.history.filter((item) => item.status === 'PASS').length
	);

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string | null): string {
		if (!isoLike) {
			return tx('未取得', 'Not available');
		}
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}
</script>

<div class="surface-stack">
	<section class="hero">
		<article class="panel panel-strong">
			<p class="eyebrow">{tx('根拠', 'Evidence')}</p>
			<h1 class="title">
				{tx(
					'答えの裏取りを、別世界の operator 画面にしないための入口です。',
					'This is the entry point for verification, not an operator-only world.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'Phase 1 では最近の証跡だけを静かに見せます。詳細比較や履歴の深掘りは main path に漏らさず、Ops 側に置きます。',
					'Phase 1 quietly exposes recent evidence artifacts. Deeper comparison and full timelines stay in Ops, not on the main path.'
				)}
			</p>
			<div class="inline-actions">
				<a class="btn-link btn-primary" href="/ops"
					>{tx('詳細比較は Ops へ', 'Open detailed comparison in Ops')}</a
				>
				<a class="btn-link btn-ghost" href="/questions">{tx('質問面へ戻る', 'Back to Questions')}</a>
			</div>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('最近の状態', 'Recent state')}</p>
			<div class="surface-meta">
				<div class="meta-card">
					<p class="meta-label">{tx('最近の証跡', 'Recent artifacts')}</p>
					<p class="meta-value">{data.history.length}</p>
				</div>
				<div class="meta-card">
					<p class="meta-label">{tx('PASS', 'PASS')}</p>
					<p class="meta-value">{recentPassCount}</p>
				</div>
			</div>
			<ul class="flat-list">
				<li>
					{tx(
						'根拠が見えない回答は成功扱いにしない。',
						'An answer without visible evidence should not count as success.'
					)}
				</li>
				<li>
					{tx(
						'不明回答も、証跡として残せる形にする。',
						'Unknown answers should also leave inspectable evidence.'
					)}
				</li>
			</ul>
		</article>
	</section>

	<section class="panel">
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('最近の証跡', 'Recent artifacts')}</p>
				<h2 class="section-title">
					{tx(
						'今は最新の evidence を静かに並べ、詳細比較は Ops 側へ残します。',
						'For now, the latest evidence is summarized here while deeper comparison stays in Ops.'
					)}
				</h2>
			</div>
		</div>

		{#if data.history.length > 0}
			<div class="card-grid">
				{#each data.history as item}
					<article class="panel surface-card">
						<div class="pipeline-head">
							<h3 class="pipeline-title">{item.schema}</h3>
							<span class={statusClass(item.status)}>{item.status}</span>
						</div>
						<p class="section-copy">{item.summary}</p>
						<div class="meta-pair">
							<p class="meta-label">{tx('証跡パス', 'Artifact path')}</p>
							<p class="path">{item.artifactPath}</p>
						</div>
						<div class="meta-pair">
							<p class="meta-label">{tx('取得時刻', 'Captured at')}</p>
							<p class="meta-copy">{dt(item.capturedAt || item.modifiedAt)}</p>
						</div>
					</article>
				{/each}
			</div>
		{:else}
			<div class="empty-state">
				<p class="section-title">{tx('まだ証跡が見つかりません。', 'No evidence artifacts were found yet.')}</p>
				<p class="section-copy">
					{tx(
						'索引作成や質問実行の後に evidence が増えます。',
						'Evidence artifacts will appear after indexing and question runs.'
					)}
				</p>
			</div>
		{/if}
	</section>
</div>
