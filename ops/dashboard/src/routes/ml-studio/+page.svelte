<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { FineTuneHistoryItem, PipelineSnapshot } from '$lib/server/types';

	interface PageData {
		ml: PipelineSnapshot | null;
		fineTuneHistory: FineTuneHistoryItem[];
		templatePreview: string;
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	let { data }: { data: PageData } = $props();

	const steps = $derived(
		localeState.value === 'ja'
			? [
					{
						title: '1. Baselineを固定する',
						command: 'make s25-ml-experiment',
						tip: '最初に baseline を固定しないと、後の改善量が比較できません。'
					},
					{
						title: '2. Prompt fine-tuneを回す',
						command:
							'python3 scripts/il_compile_prompt_loop.py --profiles v1,strict_json_v2,contract_json_v3',
						tip: 'fallback_count を最優先で下げ、objective_score は次点で見るのが安定です。'
					},
					{
						title: '3. 再評価して差分確認',
						command:
							'python3 scripts/il_compile_bench_diff.py --baseline <A> --candidate <B>',
						tip: '差分は単一指標より、再現率・妥当性・fallback理由分布で判断します。'
					}
				]
			: [
					{
						title: '1. Lock baseline',
						command: 'make s25-ml-experiment',
						tip: 'Without fixing the baseline first, later improvements are not comparable.'
					},
					{
						title: '2. Run prompt fine-tuning',
						command:
							'python3 scripts/il_compile_prompt_loop.py --profiles v1,strict_json_v2,contract_json_v3',
						tip: 'Prioritize lowering fallback_count first, then optimize objective_score.'
					},
					{
						title: '3. Re-evaluate and compare deltas',
						command:
							'python3 scripts/il_compile_bench_diff.py --baseline <A> --candidate <B>',
						tip: 'Judge with reproducibility/validity/fallback distribution, not just one metric.'
					}
				]
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

<section class="hero" style="margin-bottom: 14px;">
	<div class="panel panel-strong">
		<p class="eyebrow">ML Studio</p>
		<h1 class="title">{tx('機械学習運用チュートリアル', 'ML Operations Tutorial')}</h1>
		<p class="muted">
			{tx(
				'難しいところを先回りして、順番どおりに実行できるようにした実務向けガイドです。',
				'Practical guide that anticipates difficult points and keeps execution in a reliable sequence.'
			)}
		</p>
	</div>
	{#if data.ml}
		<div class="panel">
			<p class="eyebrow">{tx('現在のMLスナップショット', 'Current ML Snapshot')}</p>
			<h2 class="title" style="font-size: 1.25rem;">{data.ml.title}</h2>
			<div class="pipeline-head" style="margin-top: 10px;">
				<span class={statusClass(data.ml.status)}>{data.ml.status}</span>
			</div>
			{#each data.ml.metrics as metric}
				<div class="metric-row">
					<span class="metric-label">{metric.label}</span>
					<span class="metric-value">{metric.value}</span>
				</div>
			{/each}
		</div>
	{/if}
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Tutorial</p>
	<h2 class="title" style="font-size: 1.35rem;">
		{tx('自然な手順で進める3ステップ', '3 Steps with Natural Workflow')}
	</h2>
	<div class="card-grid" style="margin-top: 12px;">
		{#each steps as step}
			<article class="panel pipeline-card">
				<h3 class="pipeline-title">{step.title}</h3>
				<div class="snippet">{step.command}</div>
				<p class="muted" style="margin-top: 0;">{step.tip}</p>
			</article>
		{/each}
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Failure Tips</p>
	<h2 class="title" style="font-size: 1.2rem;">
		{tx('詰まりやすいポイント', 'Common Failure Points')}
	</h2>
	<div class="metrics-grid" style="margin-top: 10px;">
		<div class="metric-row">
			<span class="metric-label"
				>{tx('Objectiveが上がらない', 'Objective does not improve')}</span
			><span class="metric-value"
				>{tx('profile増やし過ぎを疑う', 'Too many profiles may be hurting stability')}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('再現率が落ちる', 'Reproducibility drops')}</span><span
				class="metric-value"
				>{tx('seed固定 + expand-factorを下げる', 'Fix seed + lower expand-factor')}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('fallback多発', 'Fallback spikes')}</span><span
				class="metric-value"
				>{tx(
					'strict_json_v2/contract_json_v3を優先',
					'Prioritize strict_json_v2/contract_json_v3'
				)}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('運用負荷が高い', 'Operational cost is high')}</span
			><span class="metric-value"
				>{tx(
					'AI Lab の履歴に run を集約して比較',
					'Aggregate runs in AI Lab history for easier comparison'
				)}</span
			>
		</div>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;">
	<p class="eyebrow">Template SOT</p>
	<h2 class="title" style="font-size: 1.2rem;">S25-07 Template Preview</h2>
	<div class="snippet">{data.templatePreview}</div>
</section>

<section class="panel">
	<p class="eyebrow">{tx('Fine-tune 結果', 'Fine-tune Results')}</p>
	<h2 class="title" style="font-size: 1.2rem;">
		{tx('最近のプロンプトループ履歴', 'Recent Prompt-loop History')}
	</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead
				><tr
					><th>{tx('取得時刻', 'Captured')}</th><th>Best</th><th>Objective</th><th
						>Fallback</th
					><th>{tx('レポート', 'Report')}</th></tr
				></thead
			>
			<tbody>
				{#each data.fineTuneHistory as row}
					<tr>
						<td>{dt(row.capturedAt)}</td>
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
