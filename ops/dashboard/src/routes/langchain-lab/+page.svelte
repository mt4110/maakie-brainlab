<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { AiLabRunResponse, PipelineSnapshot } from '$lib/server/types';

	interface PageData {
		langchain: PipelineSnapshot | null;
		runbookPreview: string;
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	let { data }: { data: PageData } = $props();
	let langchain = $state<PipelineSnapshot | null>(null);
	let running = $state(false);
	let error = $state('');
	let output = $state('');
	let status = $state('');

	$effect(() => {
		langchain = data.langchain;
	});

	function statusClass(value: string): string {
		return `status-pill status-${value.toLowerCase()}`;
	}

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	async function refreshOverview() {
		const res = await fetch('/api/dashboard/overview');
		if (!res.ok) {
			return;
		}
		const payload = (await res.json()) as { pipelines: PipelineSnapshot[] };
		langchain = payload.pipelines.find((row) => row.key === 'langchain') || null;
	}

	async function runLangChain() {
		running = true;
		error = '';
		output = '';
		try {
			const res = await fetch('/api/dashboard/ai-lab/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ channel: 'langchain' })
			});
			const payload = (await res.json()) as AiLabRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error || tx('LangChain 実行に失敗しました', 'LangChain run failed')
				);
			}
			status = payload.record.status;
			output = payload.record.stdout || payload.record.stderr;
			await refreshOverview();
		} catch (e) {
			error = e instanceof Error ? e.message : tx('実行に失敗しました', 'run failed');
		} finally {
			running = false;
		}
	}
</script>

<section class="hero" style="margin-bottom: 14px;">
	<div class="panel panel-strong">
		<p class="eyebrow">LangChain Lab</p>
		<h1 class="title">LangChain PoC + Rollback Ready</h1>
		<p class="muted">
			{tx(
				'PoC 実行、依存欠落時の SKIP 判定、rollback 経路まで確認できる画面です。',
				'Run PoC, verify SKIP behavior when dependencies are missing, and keep rollback paths visible.'
			)}
		</p>
	</div>
	{#if langchain}
		<div class="panel">
			<p class="eyebrow">{tx('現在のスナップショット', 'Current Snapshot')}</p>
			<h2 class="title" style="font-size: 1.2rem;">{langchain.title}</h2>
			<div class="pipeline-head" style="margin-top: 10px;">
				<span class={statusClass(langchain.status)}>{langchain.status}</span>
			</div>
			{#each langchain.metrics as metric}
				<div class="metric-row">
					<span class="metric-label">{metric.label}</span><span class="metric-value"
						>{metric.value}</span
					>
				</div>
			{/each}
		</div>
	{/if}
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Run</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('PoC 実行', 'Execute PoC')}</h2>
	<div class="actions" style="margin-top: 10px;">
		<button class="btn-primary" disabled={running} onclick={runLangChain}
			>{running
				? tx('実行中...', 'Running...')
				: tx('LangChain PoC を実行', 'Run LangChain PoC')}</button
		>
		<button class="btn-ghost" disabled={running} onclick={refreshOverview}
			>{tx('更新', 'Refresh')}</button
		>
	</div>
	{#if error}
		<p class="muted" style="color: var(--fail);">{error}</p>
	{/if}
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Tips</p>
	<h2 class="title" style="font-size: 1.2rem;">{tx('実務の観点', 'Operational Notes')}</h2>
	<div class="metrics-grid" style="margin-top: 10px;">
		<div class="metric-row">
			<span class="metric-label">{tx('依存可用性', 'Dependency availability')}</span><span
				class="metric-value"
				>{tx(
					'langchain-core 未導入時は SKIP と rollback を確認',
					'When langchain-core is missing, verify SKIP and rollback behavior'
				)}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('結合点', 'Integration point')}</span><span
				class="metric-value">retrieval rows -> runnable -> structured answer</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">rollback</span><span class="metric-value"
				>python3 scripts/ops/s25_langchain_poc.py --mode rollback-only</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('品質監視', 'Quality monitoring')}</span><span
				class="metric-value"
				>{tx(
					'expected source match を first KPI にする',
					'Use expected source match as the first KPI'
				)}</span
			>
		</div>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Runbook</p>
	<h2 class="title" style="font-size: 1.2rem;">S25-09_LANGCHAIN_POC.md</h2>
	<div class="snippet">{data.runbookPreview}</div>
</section>

{#if output}
	<section class="panel">
		<p class="eyebrow">{tx('最新出力', 'Latest Output')}</p>
		<h2 class="title" style="font-size: 1.1rem;">{status || tx('結果', 'result')}</h2>
		<div class="log-box">{output}</div>
	</section>
{/if}
