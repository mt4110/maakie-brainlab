<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type {
		AiLabChannel,
		AiLabRunRecord,
		AiLabRunResponse,
		RunInspectorRecord
	} from '$lib/server/types';

	interface PageData {
		history: AiLabRunRecord[];
		latestInspector: RunInspectorRecord | null;
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	let { data }: { data: PageData } = $props();

	let channel = $state<AiLabChannel>('local-model');
	let prompt = $state('');
	let commandTemplate = $state('');
	let profiles = $state('v1,strict_json_v2,contract_json_v3');
	let running = $state(false);
	let error = $state('');
	let latest = $state<AiLabRunRecord | null>(null);
	let history = $state<AiLabRunRecord[]>([]);
	let inspector = $state<RunInspectorRecord | null>(null);

	type InspectorTone = 'PASS' | 'WARN' | 'FAIL';

	interface InspectorBlock {
		tone: InspectorTone;
		titleJa: string;
		titleEn: string;
		summaryJa: string;
		summaryEn: string;
		details: Array<{ labelJa: string; labelEn: string; value: string }>;
	}

	interface NextActionCard {
		tone: InspectorTone;
		messageJa: string;
		messageEn: string;
		href: string;
		labelJa: string;
		labelEn: string;
	}

	$effect(() => {
		history = data.history;
		inspector = data.latestInspector;
	});

	const needsTemplate = $derived(channel === 'mcp' || channel === 'ai-cli');
	const needsProfiles = $derived(channel === 'fine-tune');

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function inspectorToneClass(tone: InspectorTone): string {
		return `inspector-card inspector-card-${tone.toLowerCase()}`;
	}

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string): string {
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function commandPlaceholder(selected: AiLabChannel): string {
		if (selected === 'mcp') {
			return tx(
				'例: npx @modelcontextprotocol/inspector --help # または {prompt} 付きのMCPクライアントコマンド',
				'Example: npx @modelcontextprotocol/inspector --help # or your MCP client command with {prompt}'
			);
		}
		if (selected === 'ai-cli') {
			return tx(
				'例: codex exec {prompt} / claude -p {prompt} / custom-ai-cli --query {prompt}',
				'Example: codex exec {prompt} / claude -p {prompt} / custom-ai-cli --query {prompt}'
			);
		}
		return '';
	}

	async function refreshHistory() {
		const res = await fetch('/api/dashboard/ai-lab/history?limit=40');
		if (!res.ok) {
			return;
		}
		const payload = (await res.json()) as { items: AiLabRunRecord[] };
		history = payload.items;
	}

	async function run() {
		error = '';
		if (
			(channel === 'local-model' || channel === 'mcp' || channel === 'ai-cli') &&
			!prompt.trim()
		) {
			error = tx('prompt を入力してください。', 'Please enter a prompt.');
			return;
		}
		running = true;
		try {
			const res = await fetch('/api/dashboard/ai-lab/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					channel,
					prompt,
					commandTemplate: needsTemplate ? commandTemplate : undefined,
					profiles: needsProfiles ? profiles : undefined
				})
			});
			const payload = (await res.json()) as AiLabRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(payload.error || tx('実行に失敗しました。', 'Run failed'));
			}
			latest = payload.record;
			if (payload.inspector) {
				inspector = payload.inspector;
			}
			await refreshHistory();
		} catch (e) {
			error = e instanceof Error ? e.message : tx('実行に失敗しました。', 'Run failed');
		} finally {
			running = false;
		}
	}

	function inspectorChunkLine(chunk: {
		sourcePath: string;
		chunkText: string;
		reason: string;
		score: number | null;
	}): string {
		const primary = chunk.sourcePath || chunk.chunkText;
		const score = chunk.score === null ? '' : ` score=${chunk.score.toFixed(3)}`;
		if (!chunk.reason) {
			return `${primary}${score}`;
		}
		return `${primary} / ${chunk.reason}${score}`;
	}

	function detectContextEmpty(record: RunInspectorRecord | null): boolean {
		if (!record) {
			return false;
		}
		if (record.source !== 'local-model') {
			return false;
		}
		const text = `${record.outputText}\n${record.errorReason}`.toLowerCase();
		return /context[^\n]*空|context\s*is\s*empty/.test(text);
	}

	function looksUnknownAnswer(record: RunInspectorRecord | null): boolean {
		if (!record) {
			return false;
		}
		const text = `${record.outputText}\n${record.errorReason}`.toLowerCase();
		return (
			/参照できる根拠が見つかりません/.test(text) ||
			/根拠:\s*-\s*不明/.test(text) ||
			/結論:\s*-\s*不明/.test(text) ||
			/no evidence retrieved/.test(text) ||
			/insufficient context/.test(text)
		);
	}

	function compactCommand(text: string, max = 96): string {
		const compact = asString(text).replace(/\s+/g, ' ').trim();
		if (!compact) {
			return '-';
		}
		return compact.length <= max ? compact : `${compact.slice(0, max)}...`;
	}

	function topChunkPreview(record: RunInspectorRecord | null): string {
		if (!record || record.retrievals.length === 0) {
			return tx('なし', 'none');
		}
		const first = record.retrievals[0];
		return first?.sourcePath || first?.sourceId || tx('参照あり', 'retrieved');
	}

	function shortReason(text: string): string {
		const compact = text.replace(/\s+/g, ' ').trim();
		if (!compact) {
			return '';
		}
		return compact.length <= 96 ? compact : `${compact.slice(0, 96)}...`;
	}

	function summarizeInspectorOutcome(record: RunInspectorRecord | null): string {
		if (!record) {
			return tx(
				'未実行です。まず上の「実行」ボタンを押してください。',
				'Not run yet. Press Run first.'
			);
		}
		const retrievalCount = record.retrievals.length;
		const hasContextEmpty = detectContextEmpty(record);
		const reason = shortReason(record.errorReason);

		if (record.status === 'PASS') {
			if (hasContextEmpty) {
				return tx(
					'PASS: 実行は成功しましたが CONTEXT が空です（根拠参照なし）。',
					'PASS: Execution succeeded but CONTEXT is empty (no evidence retrieved).'
				);
			}
			if (retrievalCount > 0) {
				return tx(
					`PASS: ${retrievalCount} 件の参照chunkを使って回答しました。`,
					`PASS: Answer generated with ${retrievalCount} retrieved chunk(s).`
				);
			}
			return tx(
				'PASS: 応答は返っています（参照chunkは0件）。',
				'PASS: Response returned (0 retrieved chunks).'
			);
		}

		if (record.status === 'WARN') {
			if (reason) {
				return tx(`WARN: ${reason}`, `WARN: ${reason}`);
			}
			return tx(
				'WARN: 実行は完了しましたが確認が必要です。',
				'WARN: Execution completed but requires review.'
			);
		}

		if (reason) {
			return tx(`FAIL: ${reason}`, `FAIL: ${reason}`);
		}
		return tx(
			'FAIL: 実行に失敗しました（詳細は下の出力を確認してください）。',
			'FAIL: Execution failed (see output details below).'
		);
	}

	function buildChatPrefillHref(record: RunInspectorRecord | null): string {
		const promptText = asString(record?.prompt).trim();
		if (!promptText) {
			return '/chat-lab';
		}
		return `/chat-lab?prefill=${encodeURIComponent(promptText)}`;
	}

	const inspectorOutcomeSummary = $derived(summarizeInspectorOutcome(inspector));

	function buildExecutionBlock(record: RunInspectorRecord | null): InspectorBlock {
		if (!record) {
			return {
				tone: 'WARN',
				titleJa: '実行結果',
				titleEn: 'Execution Result',
				summaryJa: 'まだ実行されていません。',
				summaryEn: 'No run yet.',
				details: [
					{ labelJa: '状態', labelEn: 'Status', value: '-' },
					{ labelJa: '対象', labelEn: 'Source', value: '-' },
					{ labelJa: '時間', labelEn: 'Duration', value: '-' }
				]
			};
		}
		const tone: InspectorTone = record.status === 'FAIL' ? 'FAIL' : record.status === 'WARN' ? 'WARN' : 'PASS';
		return {
			tone,
			titleJa: '実行結果',
			titleEn: 'Execution Result',
			summaryJa:
				record.status === 'PASS'
					? 'コマンド実行自体は成功しています。'
					: record.status === 'WARN'
						? '実行は完了しましたが確認が必要です。'
						: '実行に失敗しています。',
			summaryEn:
				record.status === 'PASS'
					? 'The command execution itself succeeded.'
					: record.status === 'WARN'
						? 'Execution completed but needs review.'
						: 'Execution failed.',
			details: [
				{ labelJa: '状態', labelEn: 'Status', value: record.status },
				{ labelJa: '対象', labelEn: 'Source', value: record.source || '-' },
				{ labelJa: '時間', labelEn: 'Duration', value: `${record.durationMs} ms` },
				{ labelJa: 'コマンド', labelEn: 'Command', value: compactCommand(record.command) }
			]
		};
	}

	function buildEvidenceBlock(record: RunInspectorRecord | null): InspectorBlock {
		if (!record) {
			return {
				tone: 'WARN',
				titleJa: '根拠状態',
				titleEn: 'Evidence State',
				summaryJa: 'まだ根拠状態を判定できません。',
				summaryEn: 'Evidence state not available yet.',
				details: [
					{ labelJa: '参照chunk', labelEn: 'Chunks', value: '-' },
					{ labelJa: 'CONTEXT', labelEn: 'CONTEXT', value: '-' },
					{ labelJa: '先頭参照', labelEn: 'Top Retrieval', value: '-' }
				]
			};
		}
		const retrievalCount = record.retrievals.length;
		const contextEmpty = detectContextEmpty(record);
		const tone: InspectorTone =
			retrievalCount > 0 ? 'PASS' : contextEmpty ? 'WARN' : record.status === 'FAIL' ? 'FAIL' : 'WARN';
		return {
			tone,
			titleJa: '根拠状態',
			titleEn: 'Evidence State',
			summaryJa:
				retrievalCount > 0
					? `${retrievalCount} 件の参照chunkがあります。`
					: contextEmpty
						? 'CONTEXT が空です。根拠参照なしで応答しています。'
						: '参照chunkは記録されていません。',
			summaryEn:
				retrievalCount > 0
					? `${retrievalCount} retrieved chunk(s) recorded.`
					: contextEmpty
						? 'CONTEXT is empty. The answer has no retrieved evidence.'
						: 'No retrieved chunks were recorded.',
			details: [
				{ labelJa: '参照chunk', labelEn: 'Chunks', value: String(retrievalCount) },
				{
					labelJa: 'CONTEXT',
					labelEn: 'CONTEXT',
					value: contextEmpty ? tx('空', 'empty') : tx('あり/不明', 'present or unknown')
				},
				{ labelJa: '先頭参照', labelEn: 'Top Retrieval', value: topChunkPreview(record) },
				{ labelJa: 'API Base', labelEn: 'API Base', value: record.apiBase || '-' }
			]
		};
	}

	function buildQualityBlock(record: RunInspectorRecord | null): InspectorBlock {
		if (!record) {
			return {
				tone: 'WARN',
				titleJa: '回答品質',
				titleEn: 'Answer Quality',
				summaryJa: 'まだ評価できません。',
				summaryEn: 'Quality not available yet.',
				details: [
					{ labelJa: '品質判定', labelEn: 'Quality', value: '-' },
					{ labelJa: '使用モデル', labelEn: 'Model', value: '-' },
					{ labelJa: '失敗理由', labelEn: 'Failure', value: '-' }
				]
			};
		}
		const retrievalCount = record.retrievals.length;
		const contextEmpty = detectContextEmpty(record);
		const unknown = looksUnknownAnswer(record);
		const tone: InspectorTone =
			record.status === 'FAIL'
				? 'FAIL'
				: retrievalCount > 0 && !unknown
					? 'PASS'
					: 'WARN';
		const qualityValue =
			record.status === 'FAIL'
				? tx('回答失敗', 'failed answer')
				: retrievalCount > 0 && !unknown
					? tx('根拠つき回答', 'evidence-backed answer')
					: contextEmpty
						? tx('応答あり / 根拠なし', 'response only / no evidence')
						: tx('応答あり / 要確認', 'response returned / review needed');
		return {
			tone,
			titleJa: '回答品質',
			titleEn: 'Answer Quality',
			summaryJa:
				tone === 'PASS'
					? '根拠付きで回答できています。'
					: tone === 'WARN'
						? '応答は返っていますが、そのまま信頼しない方がよい状態です。'
						: '実行失敗のため回答品質を評価できません。',
			summaryEn:
				tone === 'PASS'
					? 'The answer looks evidence-backed.'
					: tone === 'WARN'
						? 'A response exists, but it should not be trusted as-is.'
						: 'Answer quality cannot be evaluated because execution failed.',
			details: [
				{ labelJa: '品質判定', labelEn: 'Quality', value: qualityValue },
				{ labelJa: '使用モデル', labelEn: 'Model', value: record.model || '-' },
				{
					labelJa: '失敗理由',
					labelEn: 'Failure',
					value: record.errorReason ? shortReason(record.errorReason) : tx('(なし)', '(none)')
				}
			]
		};
	}

	function buildNextAction(record: RunInspectorRecord | null): NextActionCard | null {
		if (!record) {
			return {
				tone: 'WARN',
				messageJa: 'まず上の入力欄で質問を入れて実行してください。',
				messageEn: 'Enter a prompt above and run it first.',
				href: '#ai-lab-runner',
				labelJa: '上に戻る',
				labelEn: 'Back to top'
			};
		}
		const reason = `${record.errorReason}\n${record.outputText}`.toLowerCase();
		if (record.status === 'FAIL' && /404|not found|econnrefused|connection refused/.test(reason)) {
			return {
				tone: 'FAIL',
				messageJa: 'モデル接続に失敗しています。まず起動方法を確認してください。',
				messageEn: 'Model connection failed. Check startup instructions first.',
				href: '/site-docs',
				labelJa: 'サイトドキュメントで起動方法を見る',
				labelEn: 'Open Site Docs'
			};
		}
		if (detectContextEmpty(record)) {
			return {
				tone: 'WARN',
				messageJa: 'CONTEXTが空です。RAG側の状態確認に進むのが先です。',
				messageEn: 'CONTEXT is empty. Check the RAG side first.',
				href: '/rag-lab',
				labelJa: 'RAG Labで状態を再チェック',
				labelEn: 'Open RAG Lab'
			};
		}
		if (record.status === 'PASS') {
			return {
				tone: 'PASS',
				messageJa: '次は Chat + RAG で同じ質問を投げ、提案RAGと差分を見てください。',
				messageEn: 'Next, ask the same question in Chat + RAG and compare suggestions and answer.',
				href: buildChatPrefillHref(record),
				labelJa: 'Chat + RAGで同質問を試す',
				labelEn: 'Open Chat + RAG'
			};
		}
		return {
			tone: 'WARN',
			messageJa: '履歴とエラー理由を見ながら再実行条件を調整してください。',
			messageEn: 'Review history and the error reason, then adjust and retry.',
			href: '/history?source=AI_LAB',
			labelJa: '履歴を見る',
			labelEn: 'Open History'
		};
	}

	const executionBlock = $derived(buildExecutionBlock(inspector));
	const evidenceBlock = $derived(buildEvidenceBlock(inspector));
	const qualityBlock = $derived(buildQualityBlock(inspector));
	const nextActionCard = $derived(buildNextAction(inspector));

	function asString(value: unknown): string {
		if (typeof value === 'string') {
			return value;
		}
		if (value === null || value === undefined) {
			return '';
		}
		return String(value);
	}
</script>

<section class="hero" style="margin-bottom: 14px;">
	<div class="panel panel-strong">
		<p class="eyebrow">AI Lab</p>
		<h1 class="title">Local Model / MCP / AI CLI Playground</h1>
		<p class="muted">
			{tx(
				'実行結果は `.local/obs/dashboard/ai_lab_runs.jsonl` に自動登録されます。MCP/CLI は実環境に合わせて command template を指定してください（`{prompt}` が置換されます）。',
				'Run results are auto-recorded in `.local/obs/dashboard/ai_lab_runs.jsonl`. For MCP/CLI, set a command template that matches your environment (`{prompt}` will be replaced).'
			)}
		</p>
	</div>
	<div class="panel">
		<p class="eyebrow">{tx('接続メモ', 'Connector Notes')}</p>
		<h2 class="title" style="font-size: 1.25rem;">{tx('接続方式', 'Connection Types')}</h2>
		<div class="metrics-grid" style="margin-top: 10px;">
			<div class="metric-row">
				<span class="metric-label">{tx('ローカルモデル', 'Local Model')}</span><span
					class="metric-value">`src/ask.py`</span
				>
			</div>
			<div class="metric-row">
				<span class="metric-label">{tx('ファインチューン', 'Fine-tune')}</span><span
					class="metric-value">`il_compile_prompt_loop.py`</span
				>
			</div>
			<div class="metric-row">
				<span class="metric-label">MCP / AI CLI</span><span class="metric-value"
					>{tx('テンプレートコマンド', 'Template command')}</span
				>
			</div>
		</div>
	</div>
</section>

<style>
	.inspector-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 12px;
	}

	.inspector-card {
		border-radius: 18px;
		padding: 14px;
		border: 1px solid var(--line);
		background: rgba(255, 255, 255, 0.78);
		min-width: 0;
	}

	.inspector-card-pass {
		border-color: color-mix(in srgb, var(--ok) 58%, var(--line));
		background: color-mix(in srgb, var(--ok) 7%, white);
	}

	.inspector-card-warn {
		border-color: color-mix(in srgb, var(--warn) 58%, var(--line));
		background: color-mix(in srgb, var(--warn) 8%, white);
	}

	.inspector-card-fail {
		border-color: color-mix(in srgb, var(--fail) 58%, var(--line));
		background: color-mix(in srgb, var(--fail) 7%, white);
	}

	.inspector-summary {
		margin-top: 8px;
		color: var(--muted);
		line-height: 1.6;
	}

	.inspector-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}

	.inspector-detail-list {
		display: grid;
		gap: 6px;
		margin-top: 10px;
	}

	@media (max-width: 980px) {
		.inspector-grid {
			grid-template-columns: 1fr;
		}
	}
</style>

<section class="panel" id="ai-lab-runner" style="margin-bottom: 14px;">
	<p class="eyebrow">{tx('実行', 'Run')}</p>
	<h2 class="title" style="font-size: 1.4rem;">
		{tx('インタラクティブ実行コンソール', 'Interactive Command Console')}
	</h2>
	<div class="prompt-list" style="margin-top: 12px;">
		<label style="display: grid; gap: 6px;">
			<span class="eyebrow">{tx('チャネル', 'Channel')}</span>
			<select
				bind:value={channel}
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			>
				<option value="local-model"
					>{tx('local-model (ローカルモデル)', 'local-model')}</option
				>
				<option value="mcp">mcp</option>
				<option value="ai-cli">ai-cli</option>
				<option value="fine-tune"
					>{tx('fine-tune (プロンプトループ)', 'fine-tune (prompt loop)')}</option
				>
				<option value="rag-tuning">{tx('rag-tuning (RAG調整)', 'rag-tuning')}</option>
				<option value="langchain">{tx('langchain (PoC)', 'langchain')}</option>
			</select>
		</label>

		{#if channel === 'local-model' || channel === 'mcp' || channel === 'ai-cli'}
			<label style="display: grid; gap: 6px;">
				<span class="eyebrow">Prompt</span>
				<textarea
					bind:value={prompt}
					rows="4"
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				></textarea>
			</label>
		{/if}

		{#if needsTemplate}
			<label style="display: grid; gap: 6px;">
				<span class="eyebrow">{tx('コマンドテンプレート', 'Command Template')}</span>
				<input
					bind:value={commandTemplate}
					placeholder={commandPlaceholder(channel)}
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				/>
			</label>
		{/if}

		{#if needsProfiles}
			<label style="display: grid; gap: 6px;">
				<span class="eyebrow">Profiles</span>
				<input
					bind:value={profiles}
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				/>
			</label>
		{/if}

		<div class="actions">
			<button class="btn-primary" disabled={running} onclick={run}>
				{running ? tx('実行中...', 'Running...') : tx('実行', 'Run')}
			</button>
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
		<p class="eyebrow">{tx('最新結果', 'Latest Result')}</p>
		<h2 class="title" style="font-size: 1.2rem;">{latest.channel}</h2>
		<div class="metric-row">
			<span class="metric-label">{tx('ステータス', 'Status')}</span><span
				class={statusClass(latest.status)}>{latest.status}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('コマンド', 'Command')}</span><span class="metric-value"
				>{latest.command}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('時間', 'Duration')}</span><span class="metric-value"
				>{latest.durationMs} ms</span
			>
		</div>
		{#if latest.artifactPath}
			<div class="metric-row">
				<span class="metric-label">{tx('成果物', 'Artifact')}</span><span
					class="metric-value">{latest.artifactPath}</span
				>
			</div>
		{/if}
		<div class="log-box">
			{latest.stdout || tx('(stdout なし)', '(stdout empty)')}
			{latest.stderr ? `\n--- stderr ---\n${latest.stderr}` : ''}
		</div>
	</section>
{/if}

{#if inspector}
	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">{tx('Run Inspector', 'Run Inspector')}</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('実行結果 / 根拠状態 / 回答品質 / 次アクション', 'Execution / Evidence / Quality / Next Action')}
		</h2>
		<div class="panel" style="margin-top: 10px; padding: 10px 12px;">
			<p class="eyebrow">{tx('今回の成否理由（1行）', 'One-line Outcome')}</p>
			<p class="muted" style="margin-top: 6px;">{inspectorOutcomeSummary}</p>
		</div>
		<div class="inspector-grid" style="margin-top: 10px;">
			<article class={inspectorToneClass(executionBlock.tone)}>
				<div class="inspector-head">
					<p class="eyebrow">{tx(executionBlock.titleJa, executionBlock.titleEn)}</p>
					<span class={statusClass(executionBlock.tone)}>{executionBlock.tone}</span>
				</div>
				<p class="inspector-summary">{tx(executionBlock.summaryJa, executionBlock.summaryEn)}</p>
				<div class="inspector-detail-list">
					{#each executionBlock.details as item}
						<div class="metric-row">
							<span class="metric-label">{tx(item.labelJa, item.labelEn)}</span>
							<span
								class={item.value === inspector.status ? statusClass(item.value) : 'metric-value'}
								>{item.value}</span
							>
						</div>
					{/each}
				</div>
			</article>
			<article class={inspectorToneClass(evidenceBlock.tone)}>
				<div class="inspector-head">
					<p class="eyebrow">{tx(evidenceBlock.titleJa, evidenceBlock.titleEn)}</p>
					<span class={statusClass(evidenceBlock.tone)}>{evidenceBlock.tone}</span>
				</div>
				<p class="inspector-summary">{tx(evidenceBlock.summaryJa, evidenceBlock.summaryEn)}</p>
				<div class="inspector-detail-list">
					{#each evidenceBlock.details as item}
						<div class="metric-row">
							<span class="metric-label">{tx(item.labelJa, item.labelEn)}</span>
							<span class="metric-value">{item.value}</span>
						</div>
					{/each}
				</div>
			</article>
			<article class={inspectorToneClass(qualityBlock.tone)}>
				<div class="inspector-head">
					<p class="eyebrow">{tx(qualityBlock.titleJa, qualityBlock.titleEn)}</p>
					<span class={statusClass(qualityBlock.tone)}>{qualityBlock.tone}</span>
				</div>
				<p class="inspector-summary">{tx(qualityBlock.summaryJa, qualityBlock.summaryEn)}</p>
				<div class="inspector-detail-list">
					{#each qualityBlock.details as item}
						<div class="metric-row">
							<span class="metric-label">{tx(item.labelJa, item.labelEn)}</span>
							<span class="metric-value">{item.value}</span>
						</div>
					{/each}
				</div>
			</article>
			{#if nextActionCard}
				<article class={inspectorToneClass(nextActionCard.tone)}>
					<div class="inspector-head">
						<p class="eyebrow">{tx('次に押すボタン', 'Next Button')}</p>
						<span class={statusClass(nextActionCard.tone)}>{nextActionCard.tone}</span>
					</div>
					<p class="inspector-summary">
						{tx(nextActionCard.messageJa, nextActionCard.messageEn)}
					</p>
					<div class="actions" style="margin-top: 10px;">
						<a class="btn-link btn-primary" href={nextActionCard.href}>
							{tx(nextActionCard.labelJa, nextActionCard.labelEn)}
						</a>
					</div>
				</article>
			{/if}
		</div>
		<div class="card-grid" style="margin-top: 10px;">
			<article class="panel pipeline-card">
				<p class="eyebrow">{tx('返答全文', 'Full Response')}</p>
				<div class="log-box" style="margin-top: 8px;">
					{inspector.outputText || tx('(出力なし)', '(no output)')}
				</div>
			</article>
			<article class="panel pipeline-card">
				<p class="eyebrow">{tx('参照chunk一覧', 'Referenced Chunks')}</p>
				{#if inspector.retrievals.length > 0}
					<div class="prompt-list" style="margin-top: 8px;">
						{#each inspector.retrievals as chunk}
							<div class="snippet">{inspectorChunkLine(chunk)}</div>
						{/each}
					</div>
				{:else}
					<p class="muted" style="margin-top: 10px;">
						{tx('参照chunkはまだ記録されていません。', 'No referenced chunks recorded yet.')}
					</p>
				{/if}
			</article>
		</div>
	</section>
{/if}

<section class="panel">
	<p class="eyebrow">{tx('履歴', 'History')}</p>
	<h2 class="title" style="font-size: 1.25rem;">{tx('登録済み実行履歴', 'Registered Runs')}</h2>
	<div class="table-wrap">
		<table class="data-table">
			<thead>
				<tr>
					<th>{tx('時刻', 'Time')}</th>
					<th>{tx('チャネル', 'Channel')}</th>
					<th>{tx('ステータス', 'Status')}</th>
					<th>{tx('コマンド', 'Command')}</th>
					<th>Prompt</th>
				</tr>
			</thead>
			<tbody>
				{#each history as row}
					<tr>
						<td>{dt(row.createdAt)}</td>
						<td>{row.channel}</td>
						<td><span class={statusClass(row.status)}>{row.status}</span></td>
						<td class="path">{row.command}</td>
						<td>{row.prompt}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
