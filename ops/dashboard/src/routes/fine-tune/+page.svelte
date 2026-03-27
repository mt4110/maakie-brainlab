<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { AiLabRunResponse, FineTuneHistoryItem } from '$lib/server/types';

	interface PageData {
		history: FineTuneHistoryItem[];
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	let { data }: { data: PageData } = $props();

	let history = $state<FineTuneHistoryItem[]>([]);
	let profiles = $state('v1,strict_json_v2,contract_json_v3');
	let seed = $state('7');
	let running = $state(false);
	let error = $state('');
	let lastMessage = $state('');

	$effect(() => {
		history = data.history;
	});

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string): string {
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	async function refresh() {
		const res = await fetch('/api/dashboard/fine-tune/history?limit=40');
		if (!res.ok) {
			return;
		}
		const payload = (await res.json()) as { items: FineTuneHistoryItem[] };
		history = payload.items;
	}

	async function runFineTune() {
		error = '';
		lastMessage = '';
		running = true;
		try {
			const res = await fetch('/api/dashboard/ai-lab/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ channel: 'fine-tune', profiles, seed: Number(seed) })
			});
			const payload = (await res.json()) as AiLabRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error || tx('fine-tune 実行に失敗しました', 'fine-tune run failed')
				);
			}
			lastMessage = `status=${payload.record.status} exit=${payload.record.exitCode}`;
			await refresh();
		} catch (e) {
			error =
				e instanceof Error
					? e.message
					: tx('fine-tune 実行に失敗しました', 'fine-tune run failed');
		} finally {
			running = false;
		}
	}
</script>

<section class="hero" style="margin-bottom: 14px;">
	<div class="panel panel-strong">
		<p class="eyebrow">Fine-tune</p>
		<h1 class="title">
			{tx(
				'プロンプト微調整ループ (本番運用向け)',
				'Prompt Fine-tuning Loop (Production-safe)'
			)}
		</h1>
		<p class="muted">
			{tx(
				'このリポジトリでは重いモデル再学習ではなく、`scripts/il_compile_prompt_loop.py` による deterministic prompt tuning を「fine-tune相当」として運用できます。',
				'Instead of heavy model retraining, this repository uses deterministic prompt tuning via `scripts/il_compile_prompt_loop.py` as practical fine-tuning.'
			)}
		</p>
	</div>
	<div class="panel">
		<p class="eyebrow">{tx('対象', 'Scope')}</p>
		<h2 class="title" style="font-size: 1.2rem;">{tx('改善対象', 'What this improves')}</h2>
		<div class="metric-row">
			<span class="metric-label">{tx('主要', 'Primary')}</span><span class="metric-value"
				>fallback_count ↓</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('副次', 'Secondary')}</span><span class="metric-value"
				>objective_score ↑</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('出力先', 'Output')}</span><span class="metric-value"
				>.local/obs/il_compile_prompt_loop_*</span
			>
		</div>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">{tx('実行', 'Execute')}</p>
	<h2 class="title" style="font-size: 1.35rem;">
		{tx('プロンプトループ実行', 'Run Prompt Loop')}
	</h2>
	<div class="prompt-list" style="margin-top: 10px;">
		<label style="display: grid; gap: 6px;">
			<span class="eyebrow">
				{tx('Profiles (カンマ区切り)', 'Profiles (comma-separated)')}
			</span>
			<input
				bind:value={profiles}
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			/>
		</label>
		<label style="display: grid; gap: 6px; max-width: 220px;">
			<span class="eyebrow">Seed</span>
			<input
				bind:value={seed}
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			/>
		</label>
		<div class="actions">
			<button class="btn-primary" disabled={running} onclick={runFineTune}
				>{running
					? tx('実行中...', 'Running...')
					: tx('Fine-tune ループ開始', 'Start Fine-tune Loop')}</button
			>
			<button class="btn-ghost" disabled={running} onclick={refresh}
				>{tx('更新', 'Refresh')}</button
			>
		</div>
		{#if error}
			<p class="muted" style="color: var(--fail);">{error}</p>
		{/if}
		{#if lastMessage}
			<p class="muted">{lastMessage}</p>
		{/if}
	</div>
</section>

<section class="panel">
	<p class="eyebrow">{tx('履歴', 'History')}</p>
	<h2 class="title" style="font-size: 1.25rem;">
		{tx('最近のプロンプトループレポート', 'Recent Prompt-loop Reports')}
	</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead>
				<tr>
					<th>{tx('取得時刻', 'Captured')}</th>
					<th>{tx('ステータス', 'Status')}</th>
					<th>{tx('Best Profile', 'Best Profile')}</th>
					<th>{tx('Objective', 'Objective')}</th>
					<th>{tx('Fallback', 'Fallback')}</th>
					<th>{tx('レポート', 'Report')}</th>
				</tr>
			</thead>
			<tbody>
				{#each history as row}
					<tr>
						<td>{dt(row.capturedAt)}</td>
						<td><span class={statusClass(row.status)}>{row.status}</span></td>
						<td>{row.bestProfile}</td>
						<td>{row.objectiveScore ?? 'NA'}</td>
						<td>{row.fallbackCount ?? 'NA'}</td>
						<td class="path">{row.reportPath}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
