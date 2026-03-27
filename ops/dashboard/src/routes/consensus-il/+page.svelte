<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { ConsensusRecord, ConsensusRunResponse } from '$lib/server/types';

	interface PageData {
		history: ConsensusRecord[];
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	const promptJa = '同じ課題に対して、実装方針の要点を3点に整理してください。';
	const promptEn = 'Please summarize three implementation points for the same task.';

	let { data }: { data: PageData } = $props();

	let prompt = $state(promptJa);
	let cliCommandTemplate = $state('echo CLI_AGENT {prompt}');
	let apiBase = $state('');
	let apiModel = $state('');
	let apiKey = $state('');
	let running = $state(false);
	let error = $state('');
	let latest = $state<ConsensusRecord | null>(null);
	let history = $state<ConsensusRecord[]>([]);
	let lastLocale = $state(localeState.value);

	$effect(() => {
		history = data.history;
	});
	$effect(() => {
		const previousDefault = lastLocale === 'ja' ? promptJa : promptEn;
		const nextDefault = localeState.value === 'ja' ? promptJa : promptEn;
		if (prompt === previousDefault) {
			prompt = nextDefault;
		}
		lastLocale = localeState.value;
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

	async function refreshHistory() {
		const res = await fetch('/api/dashboard/consensus/history?limit=20');
		if (!res.ok) {
			return;
		}
		const payload = (await res.json()) as { items: ConsensusRecord[] };
		history = payload.items;
	}

	async function runConsensus() {
		error = '';
		running = true;
		try {
			const res = await fetch('/api/dashboard/consensus/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ prompt, cliCommandTemplate, apiBase, apiModel, apiKey })
			});
			const payload = (await res.json()) as ConsensusRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error || tx('Consensus 実行に失敗しました', 'Consensus run failed')
				);
			}
			latest = payload.record;
			await refreshHistory();
		} catch (e) {
			error =
				e instanceof Error
					? e.message
					: tx('Consensus 実行に失敗しました', 'Consensus run failed');
		} finally {
			running = false;
		}
	}
</script>

<section class="hero" style="margin-bottom: 14px;">
	<div class="panel panel-strong">
		<p class="eyebrow">Consensus IL</p>
		<h1 class="title">
			{tx('AI-to-AI 合意形成 (CLI / LOCAL / API)', 'AI-to-AI Consensus (CLI / LOCAL / API)')}
		</h1>
		<p class="muted">
			{tx(
				'同一プロンプトを複数エージェントへ投入し、`契約/ガード/エビデンス/結果/時間` を IL 監査向けにまとめます。',
				'Send the same prompt to multiple agents and summarize `contract/guard/evidence/result/time` for IL auditing.'
			)}
		</p>
	</div>
	<div class="panel">
		<p class="eyebrow">Contract</p>
		<h2 class="title" style="font-size: 1.2rem;">Default Policy</h2>
		<div class="metric-row">
			<span class="metric-label">min PASS agents</span><span class="metric-value">2</span>
		</div>
		<div class="metric-row">
			<span class="metric-label">required evidence</span><span class="metric-value">true</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">required guards</span><span class="metric-value">true</span>
		</div>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">{tx('実行入力', 'Run Inputs')}</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('実行フォーム', 'Execution Form')}</h2>
	<div class="prompt-list" style="margin-top: 12px;">
		<label style="display: grid; gap: 6px;">
			<span class="eyebrow">Prompt</span>
			<textarea
				bind:value={prompt}
				rows="4"
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			></textarea>
		</label>
		<label style="display: grid; gap: 6px;">
			<span class="eyebrow"
				>{tx(
					'CLIコマンドテンプレート (`{prompt}`)',
					'CLI command template (`{prompt}`)'
				)}</span
			>
			<input
				bind:value={cliCommandTemplate}
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			/>
		</label>
		<div
			class="card-grid"
			style="grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));"
		>
			<label style="display: grid; gap: 6px;">
				<span class="eyebrow">{tx('API base (任意)', 'API base (optional)')}</span>
				<input
					bind:value={apiBase}
					placeholder="http://127.0.0.1:11434/v1"
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				/>
			</label>
			<label style="display: grid; gap: 6px;">
				<span class="eyebrow">{tx('API model (任意)', 'API model (optional)')}</span>
				<input
					bind:value={apiModel}
					placeholder="Qwen2.5-7B-Instruct"
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				/>
			</label>
			<label style="display: grid; gap: 6px;">
				<span class="eyebrow">{tx('API key (任意)', 'API key (optional)')}</span>
				<input
					bind:value={apiKey}
					type="password"
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				/>
			</label>
		</div>
		<div class="actions">
			<button class="btn-primary" disabled={running} onclick={runConsensus}
				>{running
					? tx('実行中...', 'Running...')
					: tx('Consensus を実行', 'Run Consensus')}</button
			>
			<button class="btn-ghost" disabled={running} onclick={refreshHistory}
				>{tx('履歴を更新', 'Refresh History')}</button
			>
		</div>
		{#if error}
			<p class="muted" style="color: var(--fail);">{error}</p>
		{/if}
	</div>
</section>

{#if latest}
	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">{tx('最新Consensus', 'Latest Consensus')}</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{dt(latest.createdAt)}
		</h2>
		<div class="metric-row">
			<span class="metric-label">{tx('ステータス', 'Status')}</span><span
				class={statusClass(latest.result.status)}>{latest.result.status}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('サマリー', 'Summary')}</span><span class="metric-value"
				>{latest.result.summary}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('総時間', 'Total Time')}</span><span class="metric-value"
				>{latest.timeline.totalMs} ms</span
			>
		</div>
		<div class="snippet">{latest.result.consensusText}</div>

		<h3 style="margin-top: 12px; font-size: 1rem;">{tx('ガード', 'Guard')}</h3>
		{#if latest.guard.details.length === 0}
			<p class="muted">{tx('すべてのガードに通過しました。', 'All guards passed.')}</p>
		{:else}
			<div class="snippet">{latest.guard.details.join('\n')}</div>
		{/if}

		<h3 style="margin-top: 12px; font-size: 1rem;">Evidence</h3>
		{#if latest.evidence.refs.length === 0}
			<p class="muted">{tx('参照は検出されませんでした。', 'No refs detected.')}</p>
		{:else}
			<div class="snippet">{latest.evidence.refs.join('\n')}</div>
		{/if}
	</section>

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">{tx('エージェント出力', 'Agent Outputs')}</p>
		{#each latest.agents as agent}
			<article class="panel pipeline-card" style="margin-top: 10px;">
				<div class="pipeline-head">
					<h3 class="pipeline-title">{agent.agent}</h3>
					<span class={statusClass(agent.status)}>{agent.status}</span>
				</div>
				<div class="metric-row">
					<span class="metric-label">{tx('コマンド', 'command')}</span><span
						class="metric-value">{agent.command}</span
					>
				</div>
				<div class="metric-row">
					<span class="metric-label">{tx('時間', 'duration')}</span><span
						class="metric-value">{agent.durationMs} ms</span
					>
				</div>
				{#if agent.error}
					<div class="snippet">{agent.error}</div>
				{/if}
				{#if agent.output}
					<div class="snippet">{agent.output}</div>
				{/if}
			</article>
		{/each}
	</section>
{/if}

<section class="panel">
	<p class="eyebrow">{tx('履歴', 'History')}</p>
	<h2 class="title" style="font-size: 1.2rem;">
		{tx('最近の Consensus 実行', 'Recent Consensus Runs')}
	</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead>
				<tr>
					<th>{tx('時刻', 'Time')}</th>
					<th>{tx('ステータス', 'Status')}</th>
					<th>{tx('サマリー', 'Summary')}</th>
					<th>{tx('合計', 'Total')}</th>
					<th>Prompt</th>
				</tr>
			</thead>
			<tbody>
				{#each history as row}
					<tr>
						<td>{dt(row.createdAt)}</td>
						<td
							><span class={statusClass(row.result.status)}>{row.result.status}</span
							></td
						>
						<td>{row.result.summary}</td>
						<td>{row.timeline.totalMs} ms</td>
						<td>{row.prompt}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
