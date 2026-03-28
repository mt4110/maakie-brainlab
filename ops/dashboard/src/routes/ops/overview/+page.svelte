<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type {
		CommandRunResult,
		OverviewPayload,
		PipelineKey,
		PipelineRunResponse
	} from '$lib/server/types';

	interface PageData {
		overview: OverviewPayload;
	}

	type ProgressStage = 'IDLE' | 'RUNNING' | 'PASS' | 'FAIL';

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	let { data }: { data: PageData } = $props();

	let overviewOverride = $state<OverviewPayload | null>(null);
	const overview = $derived(overviewOverride ?? data.overview);

	let running = $state<PipelineKey | 'all' | null>(null);
	let runResponse = $state<PipelineRunResponse | null>(null);
	let runError = $state('');
	let progressStage = $state<ProgressStage>('IDLE');
	let progressMessage = $state('');
	let progressAt = $state<string | null>(null);
	let progressClearTimer = $state<ReturnType<typeof setTimeout> | null>(null);
	let refreshingOverview = $state(false);

	const PIPELINE_ORDER: PipelineKey[] = ['quality', 'operator', 'rag', 'langchain', 'ml'];

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string | null): string {
		if (!isoLike) {
			return tx('未取得', 'Not loaded');
		}
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function progressClass(stage: ProgressStage): string {
		return stage === 'RUNNING'
			? 'status-pill status-warn'
			: stage === 'PASS'
				? 'status-pill status-pass'
				: stage === 'FAIL'
					? 'status-pill status-fail'
					: 'status-pill status-unknown';
	}

	function progressLabel(stage: ProgressStage): string {
		if (stage === 'RUNNING') {
			return tx('実行中', 'RUNNING');
		}
		if (stage === 'PASS') {
			return 'PASS';
		}
		if (stage === 'FAIL') {
			return 'FAIL';
		}
		return tx('未表示', 'IDLE');
	}

	function orderedPipelines() {
		return [...overview.pipelines].sort(
			(a, b) => PIPELINE_ORDER.indexOf(a.key) - PIPELINE_ORDER.indexOf(b.key)
		);
	}

	function clearProgress(): void {
		if (progressClearTimer) {
			clearTimeout(progressClearTimer);
			progressClearTimer = null;
		}
		progressStage = 'IDLE';
		progressMessage = '';
		progressAt = null;
	}

	function scheduleProgressClear(ms: number): void {
		if (progressClearTimer) {
			clearTimeout(progressClearTimer);
		}
		progressClearTimer = setTimeout(
			() => {
				clearProgress();
			},
			Math.max(1000, ms)
		);
	}

	async function refreshOverview() {
		const res = await fetch('/api/dashboard/overview');
		if (!res.ok) {
			throw new Error(tx('状態の再読込に失敗しました。', 'Failed to reload state.'));
		}
		overviewOverride = (await res.json()) as OverviewPayload;
	}

	async function reloadOverview() {
		if (refreshingOverview) {
			return;
		}
		refreshingOverview = true;
		runError = '';
		progressStage = 'RUNNING';
		progressAt = new Date().toISOString();
		progressMessage = tx('最新状態を再読込しています。', 'Reloading current state.');
		try {
			await refreshOverview();
			progressStage = 'PASS';
			progressAt = new Date().toISOString();
			progressMessage = tx('最新状態を再読込しました。', 'Reloaded current state.');
			scheduleProgressClear(8_000);
		} catch (error) {
			progressStage = 'FAIL';
			progressAt = new Date().toISOString();
			progressMessage =
				error instanceof Error
					? error.message
					: tx('再読込に失敗しました。', 'Reload failed.');
			runError = progressMessage;
			scheduleProgressClear(20_000);
		} finally {
			refreshingOverview = false;
		}
	}

	function labelForPipeline(pipeline: PipelineKey | 'all'): string {
		if (pipeline === 'all') {
			return tx('5系統一括', 'All 5 Pipelines');
		}
		return pipeline.toUpperCase();
	}

	function runSummary(results: CommandRunResult[]): string {
		const passes = results.filter((item) => item.status === 'PASS').length;
		const warns = results.filter((item) => item.status === 'WARN').length;
		const fails = results.filter((item) => item.status === 'FAIL').length;
		return tx(
			`実行結果: PASS ${passes} / WARN ${warns} / FAIL ${fails} / TOTAL ${results.length}`,
			`Run result: PASS ${passes} / WARN ${warns} / FAIL ${fails} / TOTAL ${results.length}`
		);
	}

	function renderLog(result: CommandRunResult): string {
		const out = result.stdout || tx('(stdout なし)', '(stdout empty)');
		if (!result.stderr) {
			return out;
		}
		return `${out}\n--- stderr ---\n${result.stderr}`;
	}

	async function runPipeline(pipeline: PipelineKey | 'all') {
		if (running !== null) {
			return;
		}
		if (progressClearTimer) {
			clearTimeout(progressClearTimer);
			progressClearTimer = null;
		}
		running = pipeline;
		runError = '';
		runResponse = null;
		progressStage = 'RUNNING';
		progressAt = new Date().toISOString();
		progressMessage = tx(
			`${labelForPipeline(pipeline)} の再生成を開始しました。`,
			`Started regenerating ${labelForPipeline(pipeline)}.`
		);
		try {
			const res = await fetch('/api/dashboard/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ pipeline })
			});
			const payload = (await res.json()) as PipelineRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(payload.error || `pipeline ${pipeline} failed`);
			}
			runResponse = payload;
			await refreshOverview();
			const hasFail = payload.results.some((item) => item.status === 'FAIL');
			progressStage = hasFail ? 'FAIL' : 'PASS';
			progressAt = new Date().toISOString();
			progressMessage = hasFail
				? tx(
						`${labelForPipeline(pipeline)} の再生成は失敗を含みます。ログを確認してください。`,
						`Regeneration for ${labelForPipeline(pipeline)} includes failures. Check logs.`
					)
				: tx(
						`${labelForPipeline(pipeline)} の再生成が完了しました。`,
						`Regeneration for ${labelForPipeline(pipeline)} completed.`
					);
			scheduleProgressClear(hasFail ? 20_000 : 12_000);
		} catch (error) {
			progressStage = 'FAIL';
			progressAt = new Date().toISOString();
			progressMessage =
				error instanceof Error
					? error.message
					: tx('再生成に失敗しました。', 'Regeneration failed.');
			runError = progressMessage;
			scheduleProgressClear(20_000);
		} finally {
			running = null;
		}
	}
</script>

<div class="surface-stack">
	<section class="hero">
		<article class="panel panel-strong">
			<p class="eyebrow">Ops Overview</p>
			<h1 class="title">
				{tx(
					'全体状態の確認と既存 pipeline 再生成は、main path ではなくここに残します。',
					'Overall health inspection and existing pipeline regeneration stay here, off the main path.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'通常導線は 3 面のままにしつつ、operator に必要な overview と regenerate だけを `/ops/overview` へ退避しました。',
					'The main path remains three surfaces while the operator overview and regenerate controls move to `/ops/overview`.'
				)}
			</p>
			<div class="inline-actions">
				<a class="btn-link btn-ghost" href="/ops">{tx('Ops へ戻る', 'Back to Ops')}</a>
				<button
					class="btn-ghost"
					type="button"
					disabled={refreshingOverview}
					onclick={reloadOverview}
					data-testid="reload-overview"
				>
					{tx('最新状態を再読込', 'Reload Current State')}
				</button>
				<button
					class="btn-primary"
					type="button"
					disabled={running !== null}
					onclick={() => runPipeline('all')}
				>
					{tx('5系統を再生成', 'Regenerate All 5 Pipelines')}
				</button>
			</div>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('全体状態', 'Overall health')}</p>
			<div class="health-grid">
				<div class="health-cell">
					<p class="health-label">PASS</p>
					<p class="health-value">{overview.health.pass}</p>
				</div>
				<div class="health-cell">
					<p class="health-label">WARN</p>
					<p class="health-value">{overview.health.warn}</p>
				</div>
				<div class="health-cell">
					<p class="health-label">FAIL</p>
					<p class="health-value">{overview.health.fail}</p>
				</div>
				<div class="health-cell">
					<p class="health-label">MISSING</p>
					<p class="health-value">{overview.health.missing}</p>
				</div>
			</div>
			<p class="muted">{tx('更新', 'Generated')} {dt(overview.generatedAt)}</p>
		</article>
	</section>

	{#if progressStage !== 'IDLE' || runError}
		<section class="panel">
			<div class="pipeline-head">
				<h2 class="section-title">{tx('再生成の進行状況', 'Regeneration status')}</h2>
				<span class={progressClass(progressStage)} data-testid="run-progress">
					{progressLabel(progressStage)}
				</span>
			</div>
			<p class="section-copy">{progressMessage}</p>
			{#if progressAt}
				<p class="meta-copy">{dt(progressAt)}</p>
			{/if}
		</section>
	{/if}

	<section class="panel">
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('Pipeline 状態', 'Pipeline status')}</p>
				<h2 class="section-title">
					{tx(
						'operator が必要な health と regenerate をここに維持します。',
						'Operator health and regenerate controls remain available here.'
					)}
				</h2>
			</div>
		</div>
		<div class="card-grid">
			{#each orderedPipelines() as pipeline}
				<article class="panel pipeline-card">
					<div class="pipeline-head">
						<h3 class="pipeline-title">{pipeline.title}</h3>
						<span class={statusClass(pipeline.status)}>{pipeline.status}</span>
					</div>
					<div class="metric-row">
						<span class="metric-label">{tx('証跡', 'Artifact')}</span>
						<span class="metric-value path">{pipeline.artifactPath}</span>
					</div>
					<div class="metric-row">
						<span class="metric-label">{tx('取得時刻', 'Captured')}</span>
						<span class="metric-value">{dt(pipeline.capturedAt)}</span>
					</div>
					{#each pipeline.metrics as metric}
						<div class="metric-row">
							<span class="metric-label">{metric.label}</span>
							<span class="metric-value">{metric.value}</span>
						</div>
					{/each}
					<p class="section-copy">{pipeline.summary}</p>
					<div class="actions">
						<button
							class="btn-ghost"
							type="button"
							disabled={running !== null}
							data-testid={`regen-${pipeline.key}`}
							onclick={() => runPipeline(pipeline.key)}
						>
							{tx('再生成', 'Regenerate')}
						</button>
					</div>
				</article>
			{/each}
		</div>
	</section>

	{#if runResponse}
		<section class="panel">
			<h2 class="section-title">{tx('直近の実行結果', 'Latest run result')}</h2>
			<p class="section-copy">{runSummary(runResponse.results)}</p>
			{#each runResponse.results as result}
				<details class="prompt-item">
					<summary>
						<span>{result.pipeline}</span>
						<span class={statusClass(result.status)}>{result.status}</span>
					</summary>
					<div class="prompt-body">
						<p class="path">{result.command.join(' ')}</p>
						<pre class="log-box">{renderLog(result)}</pre>
					</div>
				</details>
			{/each}
		</section>
	{/if}
</div>
