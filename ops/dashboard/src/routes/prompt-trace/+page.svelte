<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { PromptTraceItem } from '$lib/server/types';

	interface PageData {
		prompts: PromptTraceItem[];
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	let { data }: { data: PageData } = $props();
	let keyword = $state('');
	let statusFilter = $state('ALL');

	const filtered = $derived(
		data.prompts.filter((row) => {
			const statusHit = statusFilter === 'ALL' || row.status === statusFilter;
			const keywordHit =
				!keyword.trim() ||
				row.requestText.toLowerCase().includes(keyword.toLowerCase()) ||
				row.promptPath.toLowerCase().includes(keyword.toLowerCase()) ||
				row.model.toLowerCase().includes(keyword.toLowerCase()) ||
				row.provider.toLowerCase().includes(keyword.toLowerCase());
			return statusHit && keywordHit;
		})
	);

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string): string {
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}
</script>

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">{tx('トレーサビリティ', 'Traceability')}</p>
	<h1 class="title">Prompt Trace</h1>
	<p class="muted">
		{tx(
			'`il.compile.prompt.txt` / `raw_response` / `report` を関連づけて表示します。',
			'Shows `il.compile.prompt.txt`, `raw_response`, and `report` with linked context.'
		)}
	</p>
	<div class="actions" style="margin-top: 12px;">
		<input
			type="search"
			placeholder={tx('request/model/path を検索', 'Search request/model/path')}
			bind:value={keyword}
			style="
				flex: 1;
				min-width: 220px;
				padding: 10px 12px;
				border-radius: 12px;
				border: 1px solid var(--line);
				font: inherit;
			"
		/>
		<select
			bind:value={statusFilter}
			style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
		>
			<option value="ALL">{tx('すべて', 'ALL')}</option>
			<option value="PASS">PASS</option>
			<option value="WARN">WARN</option>
			<option value="FAIL">FAIL</option>
			<option value="UNKNOWN">UNKNOWN</option>
		</select>
	</div>
</section>

<section class="panel">
	<p class="muted" style="margin-top: 0;">
		{filtered.length}
		{tx('件のプロンプト', 'prompts')}
	</p>
	<div class="prompt-list">
		{#each filtered as item}
			<details class="prompt-item">
				<summary>
					<span
						>{item.requestText ||
							tx('(リクエスト本文なし)', '(request text unavailable)')}</span
					>
					<span class={statusClass(item.status)}>{item.status}</span>
				</summary>
				<div class="prompt-body">
					<div class="path">{tx('prompt', 'prompt')}: {item.promptPath}</div>
					{#if item.responsePath}
						<div class="path">{tx('response', 'response')}: {item.responsePath}</div>
					{/if}
					{#if item.reportPath}
						<div class="path">{tx('report', 'report')}: {item.reportPath}</div>
					{/if}
					<div class="metric-row">
						<span class="metric-label">{tx('モデル', 'model')}</span>
						<span class="metric-value">{item.model || 'NA'}</span>
					</div>
					<div class="metric-row">
						<span class="metric-label">{tx('プロバイダー', 'provider')}</span>
						<span class="metric-value">{item.provider || 'NA'}</span>
					</div>
					<div class="metric-row">
						<span class="metric-label">{tx('テンプレート', 'template')}</span>
						<span class="metric-value">{item.promptTemplateId || 'NA'}</span>
					</div>
					<div class="metric-row">
						<span class="metric-label">{tx('遅延', 'latency')}</span>
						<span class="metric-value">{item.compileLatencyMs ?? 'NA'} ms</span>
					</div>
					<div class="metric-row">
						<span class="metric-label">{tx('取得時刻', 'captured')}</span>
						<span class="metric-value">{dt(item.capturedAt)}</span>
					</div>
					<div class="snippet">{item.promptPreview}</div>
					{#if item.responsePreview}
						<div class="snippet">{item.responsePreview}</div>
					{/if}
				</div>
			</details>
		{/each}
	</div>
</section>
