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

	interface PipelineGuide {
		labelJa: string;
		labelEn: string;
		summaryJa: string;
		summaryEn: string;
		inputJa: string;
		inputEn: string;
		output: string;
		resultJa: string;
		resultEn: string;
	}

	type ProgressStage = 'IDLE' | 'RUNNING' | 'PASS' | 'FAIL' | 'INFO';

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	let { data }: { data: PageData } = $props();

	let overviewOverride = $state<OverviewPayload | null>(null);
	const overview = $derived(overviewOverride ?? data.overview);

	let running = $state<PipelineKey | 'all' | null>(null);
	let runResponse = $state<PipelineRunResponse | null>(null);
	let runError = $state('');
	let tipOpen = $state<PipelineKey | null>(null);
	let progressStage = $state<ProgressStage>('IDLE');
	let progressMessage = $state('');
	let progressAt = $state<string | null>(null);
	let progressClearTimer = $state<ReturnType<typeof setTimeout> | null>(null);

	const PIPELINE_ORDER: PipelineKey[] = ['rag', 'langchain', 'ml', 'quality', 'operator'];

	const PIPELINE_GUIDES: Record<PipelineKey, PipelineGuide> = {
		rag: {
			labelJa: 'RAG調整',
			labelEn: 'RAG Tuning',
			summaryJa: 'baseline/candidate の比較指標を再計算します。',
			summaryEn: 'Recomputes baseline/candidate comparison metrics.',
			inputJa: 'index + data/raw の評価データ',
			inputEn: 'index + data/raw evaluation data',
			output: 'docs/evidence/s25-08/rag_tuning_latest.json',
			resultJa: 'Baseline Hit / Candidate Hit / Latency Delta',
			resultEn: 'Baseline Hit / Candidate Hit / Latency Delta'
		},
		langchain: {
			labelJa: 'LangChain検証',
			labelEn: 'LangChain Validation',
			summaryJa: 'PoCの疎通と期待ソース一致を再検証します。',
			summaryEn: 'Revalidates PoC connectivity and expected-source match.',
			inputJa: 'LangChain PoC 設定 + retrieval 対象データ',
			inputEn: 'LangChain PoC config + retrieval target data',
			output: 'docs/evidence/s25-09/langchain_poc_latest.json',
			resultJa: 'Retrieved Rows / PoC Backend / Expected Source Match',
			resultEn: 'Retrieved Rows / PoC Backend / Expected Source Match'
		},
		ml: {
			labelJa: 'ML評価',
			labelEn: 'ML Benchmark',
			summaryJa: 'objective/reproducible/IL妥当性スコアを更新します。',
			summaryEn: 'Updates objective/reproducible/IL validity scores.',
			inputJa: 'ML実験設定 + 評価データ',
			inputEn: 'ML experiment settings + evaluation data',
			output: 'docs/evidence/s25-07/ml_experiment_latest.json',
			resultJa: 'Objective / Reproducible / IL Validity',
			resultEn: 'Objective / Reproducible / IL Validity'
		},
		quality: {
			labelJa: '品質バーンダウン',
			labelEn: 'Quality Burndown',
			summaryJa: '完了/残件/リスク指標を再集計します。',
			summaryEn: 'Re-aggregates done/remaining/risk metrics.',
			inputJa: 'チェック結果 + 評価ログ',
			inputEn: 'check results + evaluation logs',
			output: 'docs/evidence/s30-02/quality_burndown_latest.json',
			resultJa: 'Done Checks / Remaining Checks / Risk Remaining',
			resultEn: 'Done Checks / Remaining Checks / Risk Remaining'
		},
		operator: {
			labelJa: 'Operator監視',
			labelEn: 'Operator Monitoring',
			summaryJa: '最新run_dirから成功率/遅延/再試行率を再出力します。',
			summaryEn: 'Exports success/latency/retry metrics from latest run_dir.',
			inputJa: '最新の il_thread_runner_v2 run_dir',
			inputEn: 'latest il_thread_runner_v2 run_dir',
			output: 'docs/evidence/s32-15/operator_dashboard_latest.json',
			resultJa: 'Success / Retry / P95 Latency / Throughput',
			resultEn: 'Success / Retry / P95 Latency / Throughput'
		}
	};

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string | null): string {
		if (!isoLike) {
			return tx('未取得', 'Not loaded');
		}
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function guideFor(key: PipelineKey): PipelineGuide {
		return PIPELINE_GUIDES[key];
	}

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function progressClass(stage: ProgressStage): string {
		if (stage === 'RUNNING') {
			return 'status-pill status-warn';
		}
		if (stage === 'PASS') {
			return 'status-pill status-pass';
		}
		if (stage === 'FAIL') {
			return 'status-pill status-fail';
		}
		if (stage === 'INFO') {
			return 'status-pill status-unknown';
		}
		return 'status-pill status-unknown';
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
		if (stage === 'INFO') {
			return 'INFO';
		}
		return tx('未表示', 'IDLE');
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
			progressClearTimer = null;
		}
		progressClearTimer = setTimeout(
			() => {
				clearProgress();
			},
			Math.max(1000, ms)
		);
	}

	function labelForPipeline(pipeline: PipelineKey | 'all'): string {
		if (pipeline === 'all') {
			return tx('5系統一括', 'All 5 Pipelines');
		}
		const guide = guideFor(pipeline);
		return tx(guide.labelJa, guide.labelEn);
	}

	function regenerateLabel(key: PipelineKey): string {
		const guide = guideFor(key);
		return tx(`${guide.labelJa} を再生成`, `Regenerate ${guide.labelEn}`);
	}

	function toggleTip(key: PipelineKey): void {
		tipOpen = tipOpen === key ? null : key;
	}

	async function refreshOverview() {
		const overviewRes = await fetch('/api/dashboard/overview');
		if (!overviewRes.ok) {
			throw new Error(tx('状態の再読込に失敗しました。', 'Failed to reload state.'));
		}
		overviewOverride = (await overviewRes.json()) as OverviewPayload;
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
			runError =
				error instanceof Error
					? error.message
					: tx('パイプライン実行に失敗しました。', 'Pipeline execution failed.');
			progressStage = 'FAIL';
			progressAt = new Date().toISOString();
			progressMessage = tx('再生成に失敗しました。', 'Regeneration failed.');
			scheduleProgressClear(20_000);
		} finally {
			running = null;
		}
	}

	$effect(() => {
		return () => {
			if (progressClearTimer) {
				clearTimeout(progressClearTimer);
			}
		};
	});
</script>

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">Ops Dashboard</p>
	<h1 class="title">
		{tx(
			'RAG / LangChain / ML / IL オペレーションダッシュボード',
			'RAG / LangChain / ML / IL Operations Dashboard'
		)}
	</h1>
	<p class="muted">
		{tx('最終更新:', 'Last updated:')}
		{dt(overview.generatedAt)}
	</p>
</section>

<section class="panel">
	<p class="eyebrow">{tx('操作センター', 'Action Center')}</p>
	<h2 class="title" style="font-size: 1.3rem;">{tx('5ボタン + i Tips', '5 Buttons + i Tips')}</h2>
	<p class="muted">
		{tx(
			'必要な系統だけ再生成できます。詳細は各ボタン横の i で確認してください。',
			'Run only the pipelines you need. Use the i button beside each action for details.'
		)}
	</p>

	<div class="actions" style="margin-top: 10px;">
		<button
			class="btn-ghost"
			disabled={running !== null}
			onclick={async () => {
				try {
					await refreshOverview();
					progressStage = 'INFO';
					progressAt = new Date().toISOString();
					progressMessage = tx(
						'最新状態を再読込しました（表示は数秒後に自動クリア）。',
						'Current state reloaded (this message will auto-clear).'
					);
					scheduleProgressClear(8_000);
				} catch (error) {
					progressStage = 'FAIL';
					progressAt = new Date().toISOString();
					progressMessage =
						error instanceof Error
							? error.message
							: tx('再読込に失敗しました。', 'Reload failed.');
					scheduleProgressClear(20_000);
				}
			}}
			data-testid="reload-overview">{tx('最新状態を再読込', 'Reload Current State')}</button
		>
		<button
			class="btn-ghost"
			disabled={running !== null}
			onclick={() => runPipeline('all')}
			data-testid="regen-all"
		>
			{running === 'all'
				? tx('5系統を再生成中...', 'Regenerating all 5 pipelines...')
				: tx('5系統を順番に再生成', 'Regenerate all 5 pipelines')}
		</button>
	</div>

	{#if progressStage !== 'IDLE'}
		<div class="metric-row" style="margin-top: 10px;" data-testid="run-progress">
			<span class={progressClass(progressStage)}>{progressLabel(progressStage)}</span>
			<span class="metric-value">{progressMessage}</span>
		</div>
		{#if progressAt}
			<p class="path" style="margin-top: 6px;">{dt(progressAt)}</p>
		{/if}
		<div class="actions" style="margin-top: 6px;">
			<button class="btn-ghost" type="button" onclick={clearProgress}>
				{tx('表示をクリア', 'Clear Status')}
			</button>
		</div>
	{/if}

	<div class="card-grid" style="margin-top: 10px;">
		{#each PIPELINE_ORDER as key}
			<article class="panel pipeline-card" style="padding: 10px;">
				<div class="pipeline-head">
					<h3 class="pipeline-title" style="font-size: 1rem;">
						{tx(guideFor(key).labelJa, guideFor(key).labelEn)}
					</h3>
					<button
						class="tip-icon-btn"
						type="button"
						aria-label={tx(
							`${guideFor(key).labelJa} の詳細`,
							`Details for ${guideFor(key).labelEn}`
						)}
						onclick={() => toggleTip(key)}
						data-testid={`tip-${key}`}>i</button
					>
				</div>
				<p class="muted" style="margin-top: 0;">
					{tx(guideFor(key).summaryJa, guideFor(key).summaryEn)}
				</p>
				<div class="actions" style="margin-top: 8px;">
					<button
						class="btn-primary"
						disabled={running !== null}
						onclick={() => runPipeline(key)}
						data-testid={`regen-${key}`}
					>
						{running === key
							? tx('再生成中...', 'Regenerating...')
							: regenerateLabel(key)}
					</button>
				</div>
				{#if tipOpen === key}
					<div
						class="tip-panel"
						style="margin-top: 8px;"
						data-testid={`tip-panel-${key}`}
					>
						<p class="muted" style="margin-top: 0;">
							{tx('入力', 'Input')}: {tx(
								guideFor(key).inputJa,
								guideFor(key).inputEn
							)}
						</p>
						<p class="muted" style="margin-top: 8px;">
							{tx('保存先', 'Output')}: {guideFor(key).output}
						</p>
						<p class="muted" style="margin-top: 8px;">
							{tx('結果指標', 'Result Metrics')}: {tx(
								guideFor(key).resultJa,
								guideFor(key).resultEn
							)}
						</p>
					</div>
				{/if}
			</article>
		{/each}
	</div>

	{#if runError}
		<p class="muted" style="color: var(--fail); margin-top: 10px;">{runError}</p>
	{/if}
	{#if runResponse}
		<p class="muted" style="margin-top: 10px;">{runSummary(runResponse.results)}</p>
	{/if}
</section>

{#if runResponse}
	<section class="panel" style="margin-top: 14px;">
		<p class="eyebrow">{tx('実行結果', 'Execution Result')}</p>
		<h2 class="title" style="font-size: 1.2rem;">{tx('最新の実行ログ', 'Latest Run Logs')}</h2>
		{#each runResponse.results as result}
			<details class="prompt-item" open={runResponse.results.length === 1}>
				<summary>
					<span>{result.pipeline}</span>
					<span class={statusClass(result.status)}>{result.status}</span>
				</summary>
				<div class="prompt-body">
					<div class="path">exit={result.exitCode} / {result.durationMs}ms</div>
					<div class="path">{result.command.join(' ')}</div>
					<div class="log-box">{renderLog(result)}</div>
				</div>
			</details>
		{/each}
	</section>
{/if}
