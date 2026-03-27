<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type {
		ChatRunResponse,
		ChatTurn,
		RagSourceCreateRequest,
		RagSourceItem,
		RagSuggestion,
		RunInspectorRecord
	} from '$lib/server/types';

	interface PageData {
		sources: {
			items: RagSourceItem[];
			total: number;
			page: number;
			pageSize: number;
			totalPages: number;
			query: string;
		};
		latestInspector: RunInspectorRecord | null;
		prefillMessage: string;
	}

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	let { data }: { data: PageData } = $props();

	let ragSources = $state<RagSourceItem[]>([]);
	let selectedRagIds = $state<string[]>([]);
	let searchQuery = $state('');
	let currentPage = $state(1);
	let pageSize = $state(12);
	let totalPages = $state(1);
	let totalItems = $state(0);
	let loadingSources = $state(false);
	let editorId = $state<string | null>(null);
	let sourceName = $state('');
	let sourcePath = $state('');
	let sourceTags = $state('');
	let sourceDescription = $state('');
	let sourceEnabled = $state(true);
	let sourceError = $state('');
	let savingSource = $state(false);

	let messages = $state<
		Array<{ role: 'user' | 'assistant'; content: string; createdAt: string }>
	>([]);
	let inputMessage = $state('');
	let latestSuggestions = $state<RagSuggestion[]>([]);
	let latestModel = $state('');
	let chatError = $state('');
	let chatNotice = $state('');
	let chatNoticeLevel = $state<'info' | 'ok' | 'fail'>('info');
	let chatting = $state(false);
	let inspector = $state<RunInspectorRecord | null>(null);
	let prefillApplied = $state(false);

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
		ragSources = data.sources.items;
		currentPage = data.sources.page;
		totalPages = data.sources.totalPages;
		totalItems = data.sources.total;
		pageSize = data.sources.pageSize;
		searchQuery = data.sources.query || '';
		if (selectedRagIds.length === 0) {
			selectedRagIds = data.sources.items.slice(0, 2).map((item) => item.id);
		}
		inspector = data.latestInspector;
	});

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function inspectorToneClass(tone: InspectorTone): string {
		return `inspector-card inspector-card-${tone.toLowerCase()}`;
	}

	function dt(isoLike: string): string {
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function greeting(): string {
		return tx(
			'チャットモードです。質問すると、必要に応じてRAG候補も提案します。',
			'Chat mode is ready. Ask anything and I will suggest relevant RAG sources when useful.'
		);
	}

	function ensureGreeting() {
		if (messages.length > 0) {
			return;
		}
		messages = [
			{
				role: 'assistant',
				content: greeting(),
				createdAt: new Date().toISOString()
			}
		];
	}

	$effect(() => {
		ensureGreeting();
	});

	$effect(() => {
		const candidate = (data.prefillMessage || '').trim();
		if (!candidate || prefillApplied) {
			return;
		}
		if (!inputMessage.trim()) {
			inputMessage = candidate;
		}
		chatNoticeLevel = 'info';
		chatNotice = tx(
			'AI Lab から質問を受け取りました。送信で実行できます。',
			'Question imported from AI Lab. Press Send to run.'
		);
		prefillApplied = true;
	});

	function resetEditor() {
		editorId = null;
		sourceName = '';
		sourcePath = '';
		sourceTags = '';
		sourceDescription = '';
		sourceEnabled = true;
		sourceError = '';
	}

	function startEdit(item: RagSourceItem) {
		editorId = item.id;
		sourceName = item.name;
		sourcePath = item.path;
		sourceTags = item.tags.join(', ');
		sourceDescription = item.description;
		sourceEnabled = item.enabled;
		sourceError = '';
	}

	function toggleSelected(id: string) {
		if (selectedRagIds.includes(id)) {
			selectedRagIds = selectedRagIds.filter((item) => item !== id);
		} else {
			selectedRagIds = [...selectedRagIds, id];
		}
	}

	async function loadSourcesPage(page = currentPage) {
		loadingSources = true;
		try {
			const safePage = Math.max(1, Math.trunc(page));
			const safePageSize = Math.max(5, Math.min(100, Math.trunc(pageSize)));
			const q = encodeURIComponent(searchQuery.trim());
			const res = await fetch(
				`/api/dashboard/rag-sources?q=${q}&page=${safePage}&pageSize=${safePageSize}`
			);
			if (!res.ok) {
				return;
			}
			const payload = (await res.json()) as {
				items: RagSourceItem[];
				total: number;
				page: number;
				pageSize: number;
				totalPages: number;
				query: string;
			};
			ragSources = payload.items;
			totalItems = payload.total;
			currentPage = payload.page;
			totalPages = payload.totalPages;
			pageSize = payload.pageSize;
		} finally {
			loadingSources = false;
		}
	}

	async function refreshSources() {
		await loadSourcesPage(currentPage);
	}

	async function applySearch() {
		currentPage = 1;
		await loadSourcesPage(1);
	}

	async function goPrevPage() {
		if (currentPage <= 1) {
			return;
		}
		await loadSourcesPage(currentPage - 1);
	}

	async function goNextPage() {
		if (currentPage >= totalPages) {
			return;
		}
		await loadSourcesPage(currentPage + 1);
	}

	async function saveSource() {
		sourceError = '';
		const body: RagSourceCreateRequest = {
			name: sourceName,
			path: sourcePath,
			tags: sourceTags,
			description: sourceDescription,
			enabled: sourceEnabled
		};
		if (!sourceName.trim()) {
			sourceError = tx('Name は必須です。', 'Name is required.');
			return;
		}
		savingSource = true;
		try {
			const url = editorId
				? `/api/dashboard/rag-sources/${encodeURIComponent(editorId)}`
				: '/api/dashboard/rag-sources';
			const method = editorId ? 'PATCH' : 'POST';
			const res = await fetch(url, {
				method,
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify(body)
			});
			const payload = (await res.json()) as { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error || tx('保存に失敗しました。', 'Failed to save source.')
				);
			}
			await refreshSources();
			resetEditor();
		} catch (error) {
			sourceError =
				error instanceof Error
					? error.message
					: tx('保存に失敗しました。', 'Failed to save source.');
		} finally {
			savingSource = false;
		}
	}

	async function removeSource(id: string) {
		const res = await fetch(`/api/dashboard/rag-sources/${encodeURIComponent(id)}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			return;
		}
		selectedRagIds = selectedRagIds.filter((item) => item !== id);
		await refreshSources();
		if (editorId === id) {
			resetEditor();
		}
	}

	async function toggleEnabled(item: RagSourceItem) {
		await fetch(`/api/dashboard/rag-sources/${encodeURIComponent(item.id)}`, {
			method: 'PATCH',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ enabled: !item.enabled })
		});
		await refreshSources();
	}

	async function sendMessage() {
		const text = inputMessage.trim();
		if (!text || chatting) {
			return;
		}
		chatError = '';
		chatNoticeLevel = 'info';
		chatNotice = tx(
			'送信しました。応答を待っています...',
			'Message sent. Waiting for response...'
		);
		const historyTurns: ChatTurn[] = messages.map((item) => ({
			role: item.role,
			content: item.content
		}));
		messages = [
			...messages,
			{ role: 'user', content: text, createdAt: new Date().toISOString() }
		];
		inputMessage = '';
		chatting = true;
		try {
			const res = await fetch('/api/dashboard/chat/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					message: text,
					messages: historyTurns,
					selectedRagIds
				})
			});
			const payload = (await res.json()) as ChatRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error || tx('チャット実行に失敗しました。', 'Chat execution failed.')
				);
			}
			latestSuggestions = payload.ragSuggestions || [];
			latestModel = payload.model || '';
			if (payload.inspector) {
				inspector = payload.inspector;
			}
			chatNoticeLevel = 'ok';
			chatNotice = tx('応答を受信しました。', 'Response received.');
			messages = [
				...messages,
				{
					role: 'assistant',
					content: payload.assistantMessage,
					createdAt: new Date().toISOString()
				}
			];
		} catch (error) {
			chatError =
				error instanceof Error
					? error.message
					: tx('チャット実行に失敗しました。', 'Chat execution failed.');
			chatNoticeLevel = 'fail';
			chatNotice = tx('送信に失敗しました。', 'Send failed.');
			messages = [
				...messages,
				{
					role: 'assistant',
					content: tx(
						'エラーが発生しました。ローカルモデルのAPI起動状態を確認してください。',
						'An error occurred. Please check whether the local model API is running.'
					),
					createdAt: new Date().toISOString()
				}
			];
		} finally {
			chatting = false;
		}
	}

	async function submitChat(event: SubmitEvent) {
		event.preventDefault();
		await sendMessage();
	}

	function sourceTagsText(item: RagSourceItem): string {
		if (item.tags.length === 0) {
			return tx('(タグなし)', '(no tags)');
		}
		return item.tags.join(', ');
	}

	function suggestionLabel(item: RagSuggestion): string {
		const base = `${item.name} (${item.path || '-'})`;
		if (!item.reason) {
			return base;
		}
		return `${base} / ${item.reason}`;
	}

	function topSuggestions(limit = 3): RagSuggestion[] {
		return latestSuggestions.slice(0, Math.max(1, limit));
	}

	function hiddenSuggestionCount(limit = 3): number {
		return Math.max(0, latestSuggestions.length - Math.max(1, limit));
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
		const text = `${record.outputText}\n${record.errorReason}`.toLowerCase();
		return /context[^\n]*空|context\s*is\s*empty/.test(text);
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
				'未実行です。まず質問を送信してください。',
				'Not run yet. Send a message first.'
			);
		}
		const retrievalCount = record.retrievals.length;
		const selectedCount = selectedRagCount(record);
		const hasContextEmpty = detectContextEmpty(record);
		const unknown = looksUnknownAnswer(record);
		const reason = shortReason(record.errorReason);

		if (record.status === 'PASS') {
			if (retrievalCount === 0) {
				if (selectedCount > 0) {
					return tx(
						'WARN: 選択中RAGはありますが、今回の質問に合う参照chunkは見つかりませんでした。',
						'WARN: Selected RAG exists, but no retrieved chunks matched this question.'
					);
				}
				if (hasContextEmpty || unknown) {
					return tx(
						'WARN: 応答は返りましたが、根拠参照は見つかっていません。',
						'WARN: A response was returned, but no evidence was retrieved.'
					);
				}
				return tx(
					'WARN: 応答は返りましたが参照chunkは0件です。',
					'WARN: A response was returned, but there were 0 retrieved chunks.'
				);
			}
			if (hasContextEmpty) {
				return tx(
					'PASS: 応答は返りましたが CONTEXT が空です（根拠参照なし）。',
					'PASS: Response returned but CONTEXT is empty (no evidence retrieved).'
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

	function asString(value: unknown): string {
		if (typeof value === 'string') {
			return value;
		}
		if (value === null || value === undefined) {
			return '';
		}
		return String(value);
	}

	function looksUnknownAnswer(record: RunInspectorRecord | null): boolean {
		if (!record) {
			return false;
		}
		const text = `${record.outputText}\n${record.errorReason}`.toLowerCase();
		return (
			/参照できる根拠が見つかりません/.test(text) ||
			/関連するrag候補はありません/.test(text) ||
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

	function metadataCount(value: unknown): number {
		if (typeof value === 'number' && Number.isFinite(value)) {
			return Math.max(0, Math.trunc(value));
		}
		if (Array.isArray(value)) {
			return value.length;
		}
		return 0;
	}

	function selectedRagCount(record: RunInspectorRecord | null): number {
		if (!record) {
			return 0;
		}
		return metadataCount(record.metadata.selectedRagIds);
	}

	function suggestionCount(record: RunInspectorRecord | null): number {
		if (!record) {
			return 0;
		}
		const byMeta = metadataCount(record.metadata.suggestionCount);
		return byMeta > 0 ? byMeta : record.retrievals.length;
	}

	function buildExecutionBlock(record: RunInspectorRecord | null): InspectorBlock {
		if (!record) {
			return {
				tone: 'WARN',
				titleJa: '実行結果',
				titleEn: 'Execution Result',
				summaryJa: 'まだ送信されていません。',
				summaryEn: 'No message sent yet.',
				details: [
					{ labelJa: '状態', labelEn: 'Status', value: '-' },
					{ labelJa: '対象', labelEn: 'Source', value: '-' },
					{ labelJa: '時間', labelEn: 'Duration', value: '-' }
				]
			};
		}
		const tone: InspectorTone =
			record.status === 'FAIL' ? 'FAIL' : record.status === 'WARN' ? 'WARN' : 'PASS';
		return {
			tone,
			titleJa: '実行結果',
			titleEn: 'Execution Result',
			summaryJa:
				record.status === 'PASS'
					? 'チャット実行自体は成功しています。'
					: record.status === 'WARN'
						? '実行は完了しましたが確認が必要です。'
						: 'チャット実行に失敗しています。',
			summaryEn:
				record.status === 'PASS'
					? 'The chat execution itself succeeded.'
					: record.status === 'WARN'
						? 'Execution completed but needs review.'
						: 'Chat execution failed.',
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
					{ labelJa: '提案/参照', labelEn: 'Suggestions/Retrievals', value: '-' },
					{ labelJa: '選択中RAG', labelEn: 'Selected RAG', value: '-' },
					{ labelJa: '先頭参照', labelEn: 'Top Retrieval', value: '-' }
				]
			};
		}
		const retrievalCount = record.retrievals.length;
		const contextEmpty = detectContextEmpty(record);
		const selectedCount = selectedRagCount(record);
		const suggestionTotal = suggestionCount(record);
		const tone: InspectorTone =
			retrievalCount > 0 ? 'PASS' : contextEmpty ? 'WARN' : record.status === 'FAIL' ? 'FAIL' : 'WARN';
		return {
			tone,
			titleJa: '根拠状態',
			titleEn: 'Evidence State',
			summaryJa:
				retrievalCount > 0
					? `${retrievalCount} 件の参照候補があります。`
					: selectedCount > 0
						? '選択中RAGはありますが、今回の質問に合う参照候補は見つかりませんでした。'
					: contextEmpty
						? 'CONTEXT が空です。根拠参照なしで応答しています。'
						: '参照候補はまだ記録されていません。',
			summaryEn:
				retrievalCount > 0
					? `${retrievalCount} retrieval candidate(s) recorded.`
					: selectedCount > 0
						? 'Selected RAG exists, but no evidence matched this question.'
					: contextEmpty
						? 'CONTEXT is empty. The answer has no retrieved evidence.'
						: 'No retrieval candidates were recorded.',
			details: [
				{ labelJa: '提案/参照', labelEn: 'Suggestions/Retrievals', value: String(suggestionTotal) },
				{ labelJa: '選択中RAG', labelEn: 'Selected RAG', value: String(selectedCount) },
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
		const selectedCount = selectedRagCount(record);
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
					: selectedCount > 0
						? tx('応答あり / RAG不一致', 'response only / RAG mismatch')
					: contextEmpty
						? tx('応答あり / 根拠なし', 'response only / no evidence')
						: tx('応答あり / 要確認', 'response returned / review needed');
		return {
			tone,
			titleJa: '回答品質',
			titleEn: 'Answer Quality',
			summaryJa:
				tone === 'PASS'
					? '提案RAGを使って回答できています。'
					: selectedCount > 0 && retrievalCount === 0
						? '応答は返っていますが、選択中RAGは今回の質問の根拠として使えていません。'
					: tone === 'WARN'
						? '応答は返っていますが、そのまま信頼しない方がよい状態です。'
						: '実行失敗のため回答品質を評価できません。',
			summaryEn:
				tone === 'PASS'
					? 'The answer looks supported by suggested RAG.'
					: selectedCount > 0 && retrievalCount === 0
						? 'A response exists, but the selected RAG did not support this question.'
					: tone === 'WARN'
						? 'A response exists, but it should not be trusted as-is.'
						: 'Answer quality cannot be evaluated because execution failed.',
			details: [
				{ labelJa: '品質判定', labelEn: 'Quality', value: qualityValue },
				{ labelJa: '使用モデル', labelEn: 'Model', value: record.model || latestModel || '-' },
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
				messageJa: 'まず質問を入力して送信してください。',
				messageEn: 'Enter a message and send it first.',
				href: '#chat-lab-composer',
				labelJa: 'チャット入力へ戻る',
				labelEn: 'Back to chat input'
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
		const selectedCount = selectedRagCount(record);
		if (selectedCount > 0 && record.retrievals.length === 0) {
			return {
				tone: 'WARN',
				messageJa:
					'選択中RAGと今回の質問が噛み合っていません。下のRAG一覧で別の候補を選ぶか、質問文を具体化してください。',
				messageEn:
					'The selected RAG does not match this question. Choose a different source below or make the prompt more specific.',
				href: '#chat-lab-rag-panel',
				labelJa: 'RAG一覧を見直す',
				labelEn: 'Review RAG list'
			};
		}
		if (detectContextEmpty(record) || record.retrievals.length === 0) {
			return {
				tone: 'WARN',
				messageJa: '参照候補が弱いです。下のRAG一覧で選択や有効化を見直してください。',
				messageEn: 'Retrieval is weak. Review selection/enabled state in the RAG list below.',
				href: '#chat-lab-rag-panel',
				labelJa: 'RAG一覧へ移動',
				labelEn: 'Go to RAG list'
			};
		}
		return {
			tone: 'PASS',
			messageJa: '提案RAGが出ています。次は下の候補一覧で採用したいRAGを確認してください。',
			messageEn: 'RAG suggestions are available. Review the suggested items below.',
			href: '#chat-lab-rag-panel',
			labelJa: '提案RAGを見る',
			labelEn: 'Review suggested RAG'
		};
	}

	const executionBlock = $derived(buildExecutionBlock(inspector));
	const evidenceBlock = $derived(buildEvidenceBlock(inspector));
	const qualityBlock = $derived(buildQualityBlock(inspector));
	const nextActionCard = $derived(buildNextAction(inspector));

	const inspectorOutcomeSummary = $derived(summarizeInspectorOutcome(inspector));
</script>

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

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">Chat + RAG</p>
	<h1 class="title">
		{tx('Chatモード + RAG提案 + サイドCRUD', 'Chat Mode + RAG Suggestions + Sidebar CRUD')}
	</h1>
	<p class="muted">
		{tx(
			'雑談/相談をしながら、文脈に合うRAG候補を提案します。左サイドでRAGソースの追加・更新・削除が可能です。',
			'Chat normally while receiving context-matched RAG suggestions. Use the left sidebar to create, update, and delete RAG sources.'
		)}
	</p>
</section>

<section style="display: grid; grid-template-columns: minmax(280px, 360px) 1fr; gap: 14px;">
	<aside class="panel" style="height: fit-content;">
		<p class="eyebrow">{tx('RAG管理', 'RAG Management')}</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('追加 / 編集フォーム', 'Create / Edit Form')}
		</h2>
		<div class="actions" style="margin-top: 10px;">
			<button class="btn-ghost" onclick={refreshSources}
				>{tx('一覧を更新', 'Refresh list')}</button
			>
			<button class="btn-ghost" onclick={resetEditor}>{tx('新規', 'New')}</button>
		</div>
		<div class="panel" style="margin-top: 10px;">
			<p class="eyebrow">{editorId ? tx('更新', 'Update') : tx('新規追加', 'Create')}</p>
			<div class="prompt-list">
				<label style="display: grid; gap: 6px;">
					<span class="eyebrow">Name</span>
					<input
						bind:value={sourceName}
						placeholder={tx('例: 仕様書S31', 'e.g. Spec S31')}
						style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
					/>
				</label>
				<label style="display: grid; gap: 6px;">
					<span class="eyebrow">Path</span>
					<input
						bind:value={sourcePath}
						placeholder="docs/evidence/..."
						style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
					/>
				</label>
				<label style="display: grid; gap: 6px;">
					<span class="eyebrow">{tx('タグ(カンマ区切り)', 'Tags (comma-separated)')}</span
					>
					<input
						bind:value={sourceTags}
						placeholder={tx('rag, operator, s32', 'rag, operator, s32')}
						style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
					/>
				</label>
				<label style="display: grid; gap: 6px;">
					<span class="eyebrow">{tx('説明', 'Description')}</span>
					<textarea
						bind:value={sourceDescription}
						rows="3"
						style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
					></textarea>
				</label>
				<label style="display: flex; gap: 8px; align-items: center;">
					<input type="checkbox" bind:checked={sourceEnabled} />
					<span>{tx('有効化する', 'Enabled')}</span>
				</label>
				<div class="actions">
					<button class="btn-primary" disabled={savingSource} onclick={saveSource}>
						{savingSource
							? tx('保存中...', 'Saving...')
							: editorId
								? tx('更新する', 'Update')
								: tx('追加する', 'Create')}
					</button>
					<button class="btn-ghost" disabled={savingSource} onclick={resetEditor}>
						{tx('クリア', 'Clear')}
					</button>
				</div>
				{#if sourceError}
					<p class="muted" style="color: var(--fail);">{sourceError}</p>
				{/if}
			</div>
		</div>
	</aside>

	<div>
		<section class="panel" id="chat-lab-composer" style="margin-bottom: 14px;">
			<p class="eyebrow">{tx('チャット', 'Chat')}</p>
			<h2 class="title" style="font-size: 1.3rem;">
				{tx('Chatモード', 'Chat Mode')}
			</h2>
			<div class="metric-row">
				<span class="metric-label">{tx('選択中RAG', 'Selected RAG')}</span>
				<span class="metric-value">{selectedRagIds.length}</span>
			</div>
			{#if latestModel}
				<div class="metric-row">
					<span class="metric-label">{tx('使用モデル', 'Model')}</span>
					<span class="metric-value">{latestModel}</span>
				</div>
			{/if}
			<div class="prompt-list" style="margin-top: 12px;">
				{#each messages as row}
					<article class="panel pipeline-card" style="padding: 10px;">
						<div class="pipeline-head">
							<span class="pipeline-title">{row.role}</span>
							<span class="path">{dt(row.createdAt)}</span>
						</div>
						<div
							class="snippet"
							style={row.role === 'user'
								? 'background: rgba(11, 138, 164, 0.12);'
								: 'background: rgba(16, 32, 39, 0.08);'}
						>
							{row.content}
						</div>
					</article>
				{/each}
			</div>
			<form onsubmit={submitChat}>
				<label style="display: grid; gap: 6px; margin-top: 10px;">
					<span class="eyebrow">Prompt</span>
					<textarea
						bind:value={inputMessage}
						rows="4"
						placeholder={tx(
							'質問や相談を入力してください。必要ならRAG候補を提案します。',
							'Enter your question. Relevant RAG sources will be suggested when helpful.'
						)}
						style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
					></textarea>
				</label>
				<div class="actions" style="margin-top: 10px;">
					<button
						class="btn-primary"
						type="submit"
						disabled={chatting || !inputMessage.trim()}
					>
						{chatting ? tx('送信中...', 'Sending...') : tx('送信', 'Send')}
					</button>
				</div>
			</form>
			{#if chatNotice}
				<p
					class="muted"
					style={chatNoticeLevel === 'fail'
						? 'color: var(--fail);'
						: chatNoticeLevel === 'ok'
							? 'color: var(--ok);'
							: ''}
				>
					{chatNotice}
				</p>
			{/if}
			{#if chatError}
				<p class="muted" style="color: var(--fail);">{chatError}</p>
			{/if}
		</section>

		{#if inspector}
			<section class="panel" style="margin-bottom: 14px;">
				<p class="eyebrow">{tx('Run Inspector', 'Run Inspector')}</p>
				<h2 class="title" style="font-size: 1.2rem;">
					{tx(
						'実行結果 / 根拠状態 / 回答品質 / 次アクション',
						'Execution / Evidence / Quality / Next Action'
					)}
				</h2>
				<div class="panel" style="margin-top: 10px; padding: 10px 12px;">
					<p class="eyebrow">{tx('今回の成否理由（1行）', 'One-line Outcome')}</p>
					<p class="muted" style="margin-top: 6px;">{inspectorOutcomeSummary}</p>
				</div>
				<div class="inspector-grid" style="margin-top: 10px;">
					<article class={inspectorToneClass(executionBlock.tone)}>
						<div class="inspector-head">
							<p class="eyebrow">{tx(executionBlock.titleJa, executionBlock.titleEn)}</p>
							<span class={`status-pill status-${executionBlock.tone.toLowerCase()}`}
								>{executionBlock.tone}</span
							>
						</div>
						<p class="inspector-summary">{tx(executionBlock.summaryJa, executionBlock.summaryEn)}</p>
						<div class="inspector-detail-list">
							{#each executionBlock.details as item}
								<div class="metric-row">
									<span class="metric-label">{tx(item.labelJa, item.labelEn)}</span>
									<span
										class={item.value === inspector.status ? `status-pill status-${item.value.toLowerCase()}` : 'metric-value'}
										>{item.value}</span
									>
								</div>
							{/each}
						</div>
					</article>
					<article class={inspectorToneClass(evidenceBlock.tone)}>
						<div class="inspector-head">
							<p class="eyebrow">{tx(evidenceBlock.titleJa, evidenceBlock.titleEn)}</p>
							<span class={`status-pill status-${evidenceBlock.tone.toLowerCase()}`}
								>{evidenceBlock.tone}</span
							>
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
							<span class={`status-pill status-${qualityBlock.tone.toLowerCase()}`}
								>{qualityBlock.tone}</span
							>
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
								<span class={`status-pill status-${nextActionCard.tone.toLowerCase()}`}
									>{nextActionCard.tone}</span
								>
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
							<div
								class="prompt-list"
								style="margin-top: 10px; max-height: 180px; overflow: auto;"
							>
								{#each inspector.retrievals as chunk}
									<div class="snippet">{inspectorChunkLine(chunk)}</div>
								{/each}
							</div>
						{:else}
							<p class="muted" style="margin-top: 10px;">
								{tx(
									'参照chunkはまだ記録されていません。',
									'No referenced chunks recorded yet.'
								)}
							</p>
						{/if}
					</article>
				</div>
			</section>
		{/if}

		<section class="panel" id="chat-lab-rag-panel">
			<p class="eyebrow">{tx('RAG提案', 'RAG Suggestions')}</p>
			<h2 class="title" style="font-size: 1.2rem;">
				{tx('最新ターンの提案', 'Suggestions from Latest Turn')}
			</h2>
			<p class="muted" style="margin-top: 6px;">
				{tx(
					'この欄は最新3件まで表示します（履歴は内部に保存されます）。',
					'This panel shows up to 3 latest suggestions (full history is still stored).'
				)}
			</p>
			{#if latestSuggestions.length === 0}
				<p class="muted">{tx('提案はまだありません。', 'No suggestions yet.')}</p>
			{:else}
				<div class="prompt-list" style="max-height: 180px; overflow: auto;">
					{#each topSuggestions(3) as item}
						<div class="snippet">{suggestionLabel(item)}</div>
					{/each}
				</div>
				{#if hiddenSuggestionCount(3) > 0}
					<p class="muted">
						{tx(
							`他 ${hiddenSuggestionCount(3)} 件は省略しています。`,
							`${hiddenSuggestionCount(3)} more suggestions are hidden.`
						)}
					</p>
				{/if}
			{/if}

			<div style="height: 1px; background: var(--line); margin: 12px 0;"></div>
			<p class="eyebrow">{tx('RAG一覧', 'RAG List')}</p>
			<div class="actions" style="margin-top: 8px;">
				<button class="btn-ghost" onclick={refreshSources}>{tx('更新', 'Refresh')}</button>
				<span class="metric-value">{totalItems} {tx('件', 'items')}</span>
			</div>
			<label style="display: grid; gap: 6px; margin-top: 8px;">
				<span class="eyebrow">{tx('検索', 'Search')}</span>
				<input
					bind:value={searchQuery}
					placeholder={tx(
						'名前 / path / タグ / 説明で検索',
						'Search by name / path / tag / description'
					)}
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
					onkeydown={async (event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							await applySearch();
						}
					}}
				/>
			</label>
			<div class="actions" style="margin-top: 8px;">
				<button class="btn-ghost" onclick={applySearch}>{tx('検索する', 'Search')}</button>
				<button class="btn-ghost" disabled={currentPage <= 1} onclick={goPrevPage}
					>{tx('前へ', 'Prev')}</button
				>
				<span class="metric-value">{currentPage} / {totalPages}</span>
				<button class="btn-ghost" disabled={currentPage >= totalPages} onclick={goNextPage}
					>{tx('次へ', 'Next')}</button
				>
			</div>

			<div class="prompt-list" style="margin-top: 10px; max-height: 52vh; overflow: auto;">
				{#if loadingSources}
					<p class="muted">{tx('読み込み中...', 'Loading...')}</p>
				{/if}
				{#if !loadingSources && ragSources.length === 0}
					<p class="muted">
						{tx('該当するRAGソースがありません。', 'No matching RAG sources.')}
					</p>
				{/if}
				{#each ragSources as item}
					<article class="panel pipeline-card" style="padding: 10px;">
						<div class="pipeline-head">
							<label style="display: flex; gap: 8px; align-items: center;">
								<input
									type="checkbox"
									checked={selectedRagIds.includes(item.id)}
									onchange={() => toggleSelected(item.id)}
								/>
								<span class="pipeline-title">{item.name}</span>
							</label>
							<span
								class={`status-pill ${item.enabled ? 'status-pass' : 'status-unknown'}`}
							>
								{item.enabled ? 'ON' : 'OFF'}
							</span>
						</div>
						<div class="path">{item.path || '-'}</div>
						<div class="metric-row">
							<span class="metric-label">{tx('タグ', 'tags')}</span>
							<span class="metric-value">{sourceTagsText(item)}</span>
						</div>
						<div class="actions">
							<button class="btn-ghost" onclick={() => startEdit(item)}
								>{tx('編集', 'Edit')}</button
							>
							<button class="btn-ghost" onclick={() => toggleEnabled(item)}>
								{item.enabled ? tx('無効化', 'Disable') : tx('有効化', 'Enable')}
							</button>
							<button class="btn-ghost" onclick={() => removeSource(item.id)}
								>{tx('削除', 'Delete')}</button
							>
						</div>
					</article>
				{/each}
			</div>
		</section>
	</div>
</section>
