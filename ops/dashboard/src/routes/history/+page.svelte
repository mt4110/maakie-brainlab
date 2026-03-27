<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { EvidenceHistoryItem, RunInspectorHistoryItem } from '$lib/server/types';

	interface PageData {
		history: EvidenceHistoryItem[];
		runHistory: RunInspectorHistoryItem[];
	}
	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	type SourceFilter = 'ALL' | 'EVIDENCE' | 'AI_LAB' | 'CHAT_RAG';
	type TimelineSource = 'EVIDENCE' | 'AI_LAB' | 'CHAT_RAG';

	interface TimelineItem {
		id: string;
		source: TimelineSource;
		status: string;
		capturedAt: string;
		schema: string;
		artifactPath: string;
		summary: string;
		inspectHref: string | null;
		searchBlob: string;
	}

	interface DiffSummary {
		addedCount: number;
		removedCount: number;
		changedCount: number;
	}

	interface DiffKeyDelta {
		path: string;
		left: string;
		right: string;
	}

	interface DiffHighlights {
		added: DiffKeyDelta[];
		removed: DiffKeyDelta[];
		changed: DiffKeyDelta[];
	}

	type CompareTone = 'PASS' | 'WARN' | 'FAIL' | 'UNKNOWN';

	let { data }: { data: PageData } = $props();
	let keyword = $state('');
	let statusFilter = $state('ALL');
	let sourceFilter = $state<SourceFilter>('ALL');
	let leftId = $state('');
	let rightId = $state('');
	let leftPayload = $state<unknown | null>(null);
	let rightPayload = $state<unknown | null>(null);
	let compareRunning = $state(false);
	let compareError = $state('');
	let compareNotice = $state('');
	let compareNoticeLevel = $state<'info' | 'ok' | 'fail'>('info');
	let diffSummary = $state<DiffSummary | null>(null);
	let diffHighlights = $state<DiffHighlights>({ added: [], removed: [], changed: [] });
	let compareCopying = $state(false);
	let compareSectionEl = $state<HTMLElement | null>(null);
	let compareQueryApplied = $state(false);

	const timeline = $derived<TimelineItem[]>(
		[
			...data.history.map((row) => {
				const capturedAt = row.capturedAt || row.modifiedAt;
				return {
					id: `evidence:${row.id}`,
					source: 'EVIDENCE' as const,
					status: row.status,
					capturedAt,
					schema: row.schema,
					artifactPath: row.artifactPath,
					summary: row.summary,
					inspectHref: null,
					searchBlob: `${row.artifactPath} ${row.schema} ${row.summary}`
				};
			}),
			...data.runHistory.map((row) => {
				const source = row.scope === 'ai-lab' ? ('AI_LAB' as const) : ('CHAT_RAG' as const);
				const schema = row.model || row.source || 'run_inspector';
				return {
					id: `run:${row.id}`,
					source,
					status: row.status,
					capturedAt: row.createdAt,
					schema,
					artifactPath: `run_inspector:${row.id}`,
					summary: row.summary,
					inspectHref: row.scope === 'ai-lab' ? '/ai-lab' : '/chat-lab',
					searchBlob: `${row.prompt} ${row.summary} ${row.model} ${row.source} ${row.errorReason}`
				};
			})
		].sort((a, b) => new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime())
	);

	const filtered = $derived(
		timeline.filter((row) => {
			const keywordHit =
				!keyword.trim() ||
				row.searchBlob.toLowerCase().includes(keyword.toLowerCase()) ||
				row.artifactPath.toLowerCase().includes(keyword.toLowerCase()) ||
				row.schema.toLowerCase().includes(keyword.toLowerCase());
			const statusHit = statusFilter === 'ALL' || row.status === statusFilter;
			const sourceHit = sourceFilter === 'ALL' || row.source === sourceFilter;
			return keywordHit && statusHit && sourceHit;
		})
	);
	const leftItem = $derived(data.history.find((row) => row.id === leftId) ?? null);
	const rightItem = $derived(data.history.find((row) => row.id === rightId) ?? null);
	const isSameCompareTarget = $derived(!!leftId && !!rightId && leftId === rightId);
	const compareDisabled = $derived(
		compareRunning || !leftItem || !rightItem || isSameCompareTarget
	);
	const compareTone = $derived(compareToneFromStatuses(leftItem?.status, rightItem?.status));

	$effect(() => {
		if (!compareQueryApplied && typeof window !== 'undefined') {
			const params = new URLSearchParams(window.location.search);
			const queryLeft = params.get('left');
			const queryRight = params.get('right');
			if (queryLeft && data.history.some((row) => row.id === queryLeft)) {
				leftId = queryLeft;
			}
			if (queryRight && data.history.some((row) => row.id === queryRight)) {
				rightId = queryRight;
			}
			compareQueryApplied = true;
		}
		if (!leftId && data.history.length > 0) {
			leftId = data.history[0].id;
		}
		if (
			(!rightId || rightId === leftId) &&
			data.history.length > 1 &&
			data.history[1] &&
			data.history[1].id !== leftId
		) {
			rightId = data.history[1].id;
		}
	});

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function compareToneFromStatuses(
		leftStatus: string | null | undefined,
		rightStatus: string | null | undefined
	): CompareTone | null {
		if (!leftStatus || !rightStatus) {
			return null;
		}
		const statuses = [leftStatus, rightStatus].map((status) => status.toUpperCase());
		if (statuses.includes('FAIL')) {
			return 'FAIL';
		}
		if (statuses.includes('WARN')) {
			return 'WARN';
		}
		if (statuses.every((status) => status === 'PASS')) {
			return 'PASS';
		}
		return 'UNKNOWN';
	}

	function normalizeIsoDate(value: string): number {
		const ms = new Date(value).getTime();
		return Number.isFinite(ms) ? ms : 0;
	}

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string): string {
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function shortArtifactPath(artifactPath: string, max = 56): string {
		const path = artifactPath.trim();
		if (path.length <= max) {
			return path;
		}
		const keep = Math.max(10, max - 3);
		return `...${path.slice(path.length - keep)}`;
	}

	function compareOptionLabel(item: EvidenceHistoryItem): string {
		const captured = dt(item.capturedAt || item.modifiedAt);
		const short = shortArtifactPath(item.artifactPath, 52);
		return `${captured} | ${item.status} | ${short}`;
	}

	function scalarText(value: unknown): string {
		if (value === null) {
			return 'null';
		}
		if (value === undefined) {
			return 'undefined';
		}
		if (typeof value === 'string') {
			return value;
		}
		return JSON.stringify(value);
	}

	function flattenJson(
		value: unknown,
		prefix: string,
		out: Map<string, string>,
		depth = 0
	): void {
		if (out.size >= 1200) {
			return;
		}
		if (depth > 6) {
			out.set(prefix || '$', '[depth-limit]');
			return;
		}
		if (value === null || value === undefined) {
			out.set(prefix || '$', scalarText(value));
			return;
		}
		if (Array.isArray(value)) {
			if (value.length === 0) {
				out.set(prefix || '$', '[]');
				return;
			}
			for (let i = 0; i < value.length; i += 1) {
				if (out.size >= 1200) {
					return;
				}
				const next = prefix ? `${prefix}[${i}]` : `$[${i}]`;
				flattenJson(value[i], next, out, depth + 1);
			}
			return;
		}
		if (typeof value === 'object') {
			const record = value as Record<string, unknown>;
			const keys = Object.keys(record).sort();
			if (keys.length === 0) {
				out.set(prefix || '$', '{}');
				return;
			}
			for (const key of keys) {
				if (out.size >= 1200) {
					return;
				}
				const next = prefix ? `${prefix}.${key}` : `$.${key}`;
				flattenJson(record[key], next, out, depth + 1);
			}
			return;
		}
		out.set(prefix || '$', scalarText(value));
	}

	function buildDiffSummary(left: unknown, right: unknown): DiffSummary | null {
		if (left === null || right === null) {
			return null;
		}
		const leftFlat = new Map<string, string>();
		const rightFlat = new Map<string, string>();
		flattenJson(left, '$', leftFlat);
		flattenJson(right, '$', rightFlat);
		const keys = new Set<string>([...leftFlat.keys(), ...rightFlat.keys()]);
		let addedCount = 0;
		let removedCount = 0;
		let changedCount = 0;

		for (const key of [...keys].sort()) {
			const hasLeft = leftFlat.has(key);
			const hasRight = rightFlat.has(key);
			const leftValue = leftFlat.get(key) ?? '';
			const rightValue = rightFlat.get(key) ?? '';
			if (!hasLeft && hasRight) {
				addedCount += 1;
				continue;
			}
			if (hasLeft && !hasRight) {
				removedCount += 1;
				continue;
			}
			if (leftValue !== rightValue) {
				changedCount += 1;
			}
		}

		return { addedCount, removedCount, changedCount };
	}

	function compactValue(value: string, max = 64): string {
		if (value.length <= max) {
			return value;
		}
		return `${value.slice(0, max - 1)}...`;
	}

	function buildDiffHighlights(left: unknown, right: unknown, limit = 4): DiffHighlights {
		const leftFlat = new Map<string, string>();
		const rightFlat = new Map<string, string>();
		flattenJson(left, '$', leftFlat);
		flattenJson(right, '$', rightFlat);
		const keys = [...new Set<string>([...leftFlat.keys(), ...rightFlat.keys()])].sort();
		const added: DiffKeyDelta[] = [];
		const removed: DiffKeyDelta[] = [];
		const changed: DiffKeyDelta[] = [];

		for (const key of keys) {
			const hasLeft = leftFlat.has(key);
			const hasRight = rightFlat.has(key);
			const leftValue = leftFlat.get(key) ?? '';
			const rightValue = rightFlat.get(key) ?? '';
			if (!hasLeft && hasRight) {
				if (added.length < limit) {
					added.push({ path: key, left: '-', right: compactValue(rightValue) });
				}
				continue;
			}
			if (hasLeft && !hasRight) {
				if (removed.length < limit) {
					removed.push({ path: key, left: compactValue(leftValue), right: '-' });
				}
				continue;
			}
			if (leftValue !== rightValue && changed.length < limit) {
				changed.push({
					path: key,
					left: compactValue(leftValue),
					right: compactValue(rightValue)
				});
			}
		}

		return { added, removed, changed };
	}

	function sourceLabel(source: TimelineSource): string {
		if (source === 'AI_LAB') {
			return 'AI Lab';
		}
		if (source === 'CHAT_RAG') {
			return 'Chat + RAG';
		}
		return tx('Evidence', 'Evidence');
	}

	function setCompareNotice(level: 'info' | 'ok' | 'fail', message: string): void {
		compareNoticeLevel = level;
		compareNotice = message;
	}

	function latestTwoPair(): [EvidenceHistoryItem, EvidenceHistoryItem] | null {
		if (!data.history[0] || !data.history[1]) {
			return null;
		}
		return [data.history[0], data.history[1]];
	}

	function orderPairByCaptured(
		a: EvidenceHistoryItem,
		b: EvidenceHistoryItem
	): [EvidenceHistoryItem, EvidenceHistoryItem] {
		const aTs = normalizeIsoDate(a.capturedAt || a.modifiedAt);
		const bTs = normalizeIsoDate(b.capturedAt || b.modifiedAt);
		return aTs >= bTs ? [a, b] : [b, a];
	}

	function evidencePairForRow(targetId: string): [EvidenceHistoryItem, EvidenceHistoryItem] | null {
		const targetIndex = data.history.findIndex((row) => row.id === targetId);
		if (targetIndex < 0) {
			return null;
		}
		const target = data.history[targetIndex];
		if (!target) {
			return null;
		}
		const sameArtifactOlder = data.history
			.slice(targetIndex + 1)
			.find((row) => row.artifactPath === target.artifactPath);
		if (sameArtifactOlder) {
			return orderPairByCaptured(target, sameArtifactOlder);
		}
		const previousAny = data.history.find((row) => row.id !== target.id);
		if (!previousAny) {
			return null;
		}
		return orderPairByCaptured(target, previousAny);
	}

	function scrollCompareIntoView(): void {
		if (!compareSectionEl || typeof window === 'undefined') {
			return;
		}
		compareSectionEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	function sameArtifactPair(): [EvidenceHistoryItem, EvidenceHistoryItem] | null {
		if (data.history.length < 2) {
			return null;
		}
		const pivot = data.history.find((row) => row.id === leftId) || data.history[0];
		if (!pivot) {
			return null;
		}
		const same = data.history.filter((row) => row.artifactPath === pivot.artifactPath);
		if (same.length >= 2) {
			return [same[0], same[1]];
		}
		return latestTwoPair();
	}

	function selectLatestTwo(): void {
		const pair = latestTwoPair();
		if (!pair) {
			setCompareNotice(
				'fail',
				tx('比較対象が不足しています。', 'Not enough items for comparison.')
			);
			return;
		}
		leftId = pair[0].id;
		rightId = pair[1].id;
		setCompareNotice(
			'info',
			tx(
				'左=最新、右=1つ前を選択しました。次に「JSONを比較」を押してください。',
				'Selected Left=latest and Right=previous. Press Compare JSON next.'
			)
		);
	}

	function selectLatestSameArtifactPair(): void {
		const pair = sameArtifactPair();
		if (!pair) {
			setCompareNotice(
				'fail',
				tx(
					'同一Artifactで比較できる履歴がありません。',
					'No comparable history for same artifact.'
				)
			);
			return;
		}
		leftId = pair[0].id;
		rightId = pair[1].id;
		setCompareNotice(
			'info',
			tx(
				'同じArtifactの新旧を選択しました。次に「JSONを比較」を押してください。',
				'Selected newer/older of same artifact. Press Compare JSON next.'
			)
		);
	}

	async function quickCompareFromRow(item: TimelineItem): Promise<void> {
		if (item.source !== 'EVIDENCE') {
			return;
		}
		const evidenceId = item.id.replace(/^evidence:/, '');
		const pair = evidencePairForRow(evidenceId);
		if (!pair) {
			setCompareNotice(
				'fail',
				tx('比較できる2件が見つかりません。', 'Could not find two items to compare.')
			);
			return;
		}
		leftId = pair[0].id;
		rightId = pair[1].id;
		setCompareNotice(
			'info',
			tx(
				'履歴行から2件を選択しました。比較を実行します。',
				'Selected two records from timeline. Running comparison.'
			)
		);
		scrollCompareIntoView();
		await comparePair(pair[0], pair[1]);
	}

	async function fetchArtifact(artifactPath: string): Promise<unknown> {
		const res = await fetch(`/api/dashboard/evidence?path=${encodeURIComponent(artifactPath)}`);
		const payload = (await res.json()) as { item?: unknown; error?: string };
		if (!res.ok || payload.error) {
			throw new Error(
				payload.error ||
					tx(
						'Evidence artifact の取得に失敗しました。',
						'Failed to fetch evidence artifact.'
					)
			);
		}
		return payload.item ?? null;
	}

	async function comparePair(
		leftEvidence: EvidenceHistoryItem,
		rightEvidence: EvidenceHistoryItem
	): Promise<void> {
		compareRunning = true;
		compareError = '';
		leftPayload = null;
		rightPayload = null;
		diffSummary = null;
		diffHighlights = { added: [], removed: [], changed: [] };
		try {
			const [left, right] = await Promise.all([
				fetchArtifact(leftEvidence.artifactPath),
				fetchArtifact(rightEvidence.artifactPath)
			]);
			leftPayload = left;
			rightPayload = right;
			const summary = buildDiffSummary(left, right);
			diffSummary = summary;
			diffHighlights = buildDiffHighlights(left, right);
			if (summary) {
				setCompareNotice(
					'ok',
					tx(
						`比較完了: 追加 ${summary.addedCount} / 削除 ${summary.removedCount} / 変更 ${summary.changedCount}`,
						`Compared: +${summary.addedCount} / -${summary.removedCount} / changed ${summary.changedCount}`
					)
				);
			} else {
				setCompareNotice('ok', tx('比較完了。', 'Comparison complete.'));
			}
		} catch (error) {
			compareError =
				error instanceof Error
					? error.message
					: tx('Evidence比較に失敗しました。', 'Evidence comparison failed.');
			setCompareNotice('fail', tx('比較に失敗しました。', 'Comparison failed.'));
			diffSummary = null;
			diffHighlights = { added: [], removed: [], changed: [] };
		} finally {
			compareRunning = false;
		}
	}

	async function compareSelected() {
		if (!leftItem || !rightItem) {
			compareError = tx(
				'2つのEvidenceを選択してください。',
				'Please select two evidence items.'
			);
			setCompareNotice(
				'fail',
				tx('左と右の両方を選択してください。', 'Please select both left and right items.')
			);
			return;
		}
		if (leftId === rightId) {
			compareError = tx(
				'同じ項目が左右で選択されています。',
				'The same item is selected for both sides.'
			);
			setCompareNotice(
				'fail',
				tx(
					'左右で異なる項目を選択してください。',
					'Choose different items for left and right.'
				)
			);
			return;
		}
		await comparePair(leftItem, rightItem);
	}

	function compareResultShareText(): string | null {
		if (!leftItem || !rightItem) {
			return null;
		}
		const lines: string[] = [];
		lines.push('[History Compare]');
		if (compareTone) {
			lines.push(`Result: ${compareTone}`);
		}
		lines.push(`Left : ${leftItem.artifactPath} (${leftItem.status})`);
		lines.push(`Right: ${rightItem.artifactPath} (${rightItem.status})`);
		lines.push(
			`Captured: ${dt(leftItem.capturedAt || leftItem.modifiedAt)} -> ${dt(
				rightItem.capturedAt || rightItem.modifiedAt
			)}`
		);
		if (diffSummary) {
			lines.push(
				`Diff: +${diffSummary.addedCount} / -${diffSummary.removedCount} / changed ${diffSummary.changedCount}`
			);
		}
		if (diffHighlights.changed.length > 0) {
			lines.push(
				`Changed keys: ${diffHighlights.changed.map((item) => item.path).join(', ')}`
			);
		}
		if (typeof window !== 'undefined') {
			const url = new URL(window.location.href);
			url.searchParams.set('left', leftItem.id);
			url.searchParams.set('right', rightItem.id);
			lines.push(`Share: ${url.toString()}`);
		}
		return lines.join('\n');
	}

	async function copyCompareResult(): Promise<void> {
		const payload = compareResultShareText();
		if (!payload) {
			setCompareNotice(
				'fail',
				tx('先に比較対象を選択してください。', 'Please select compare targets first.')
			);
			return;
		}
		if (typeof navigator === 'undefined' || !navigator.clipboard) {
			setCompareNotice(
				'fail',
				tx(
					'このブラウザはクリップボードコピーに対応していません。',
					'This browser does not support clipboard copy.'
				)
			);
			return;
		}
		compareCopying = true;
		try {
			await navigator.clipboard.writeText(payload);
			setCompareNotice(
				'ok',
				tx('比較結果をコピーしました。共有に貼り付けできます。', 'Copied compare result. Ready to share.')
			);
		} catch {
			setCompareNotice(
				'fail',
				tx('コピーに失敗しました。もう一度試してください。', 'Copy failed. Please try again.')
			);
		} finally {
			compareCopying = false;
		}
	}

	function swapCompareSides(): void {
		if (!leftId || !rightId) {
			setCompareNotice(
				'fail',
				tx(
					'左右を入れ替えるには両方の選択が必要です。',
					'Both left and right selections are required to swap.'
				)
			);
			return;
		}
		const nextLeft = rightId;
		const nextRight = leftId;
		leftId = nextLeft;
		rightId = nextRight;
		setCompareNotice(
			'info',
			tx(
				'左右を入れ替えました。必要なら「JSONを比較」を押してください。',
				'Swapped left and right. Press Compare if needed.'
			)
		);
	}

	function prettyJson(value: unknown): string {
		return JSON.stringify(value, null, 2);
	}
</script>

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">{tx('エビデンスタイムライン', 'Evidence Timeline')}</p>
	<h1 class="title">{tx('エビデンス履歴', 'Evidence History')}</h1>
	<p class="muted">
		{tx(
			'`docs/evidence/**/_latest.json` / Consensus Contract違反ログ / Run Inspector（AI Lab・Chat + RAG）を時系列で表示します。',
			'Shows `docs/evidence/**/_latest.json`, consensus contract-violation logs, and Run Inspector (AI Lab / Chat + RAG) over time.'
		)}
	</p>
	<div class="prompt-list" style="margin-top: 10px;">
		<div class="snippet">
			{tx(
				'このページは「Evidence JSON（成果物）」の履歴です。チャット本文やAI実行結果の本文履歴ではありません。',
				'This page shows Evidence JSON artifact history, not full chat/body logs.'
			)}
		</div>
		<div class="snippet">
			{tx(
				'AI実行本文は AI Lab / Chat + RAG の Run Inspector を確認してください。',
				'For full AI run text, use Run Inspector in AI Lab / Chat + RAG.'
			)}
		</div>
		<div class="snippet">
			{tx(
				'フィルタ「AI Lab / Chat + RAG」を使うと、Run Inspector実行履歴だけに絞り込めます。',
				'Use the AI Lab / Chat + RAG filter to focus only on Run Inspector runs.'
			)}
		</div>
	</div>
	<div class="actions" style="margin-top: 10px;">
		<a class="btn-link btn-ghost" href="/ai-lab">{tx('AI Labを開く', 'Open AI Lab')}</a>
		<a class="btn-link btn-ghost" href="/chat-lab"
			>{tx('Chat + RAGを開く', 'Open Chat + RAG')}</a
		>
	</div>
	<div class="actions" style="margin-top: 12px;">
		<input
			type="search"
			placeholder={tx(
				'path/schema/summary/prompt で検索',
				'Search path/schema/summary/prompt'
			)}
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
			bind:value={sourceFilter}
			style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
		>
			<option value="ALL">{tx('全ソース', 'All Sources')}</option>
			<option value="EVIDENCE">{tx('Evidence', 'Evidence')}</option>
			<option value="AI_LAB">AI Lab</option>
			<option value="CHAT_RAG">Chat + RAG</option>
		</select>
		<select
			bind:value={statusFilter}
			style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
		>
			<option value="ALL">{tx('すべて', 'ALL')}</option>
			<option value="PASS">PASS</option>
			<option value="WARN">WARN</option>
			<option value="FAIL">FAIL</option>
			<option value="SKIP">SKIP</option>
			<option value="UNKNOWN">UNKNOWN</option>
			<option value="MISSING">MISSING</option>
		</select>
	</div>
</section>

<section class="panel" style="margin-bottom: 14px;" bind:this={compareSectionEl}>
	<p class="eyebrow">{tx('比較', 'Compare')}</p>
	<h2 class="title" style="font-size: 1.3rem;">
		{tx('Evidence JSON 差分比較', 'Evidence JSON Diff Compare')}
	</h2>
	<p class="muted" style="margin-top: 8px;">
		{tx(
			'初学者向けの固定導線です。1) 左右を自動選択 2) JSONを比較 3) 変更キーを確認',
			'Beginner fixed flow: 1) Auto-select left/right 2) Compare JSON 3) Review changed keys'
		)}
	</p>
		<div class="compare-quick-flow" style="margin-top: 10px;">
			<button class="btn-primary" onclick={selectLatestTwo}>
				{tx('1. 左=最新 / 右=1つ前を選択', '1. Select latest and previous')}
			</button>
			<button class="btn-primary" disabled={compareDisabled} onclick={compareSelected}>
				{compareRunning ? tx('比較中...', 'Comparing...') : tx('2. JSONを比較', '2. Compare JSON')}
			</button>
			<button
				class="btn-ghost"
				disabled={!leftItem || !rightItem || compareCopying}
				onclick={() => void copyCompareResult()}
			>
				{compareCopying
					? tx('コピー中...', 'Copying...')
					: tx('結果をコピー/共有', 'Copy/Share result')}
			</button>
		</div>
		<p class="muted" style="margin-top: 8px;">
			{tx(
				'3. 比較後に「変更キー（短い要約）」で差分を確認し、必要ならコピー共有します。',
				'3. Review changed keys, then copy/share when needed.'
			)}
		</p>
	{#if compareNotice}
		<p
			class="muted"
			style={compareNoticeLevel === 'fail'
				? 'color: var(--fail); margin-top: 8px;'
				: compareNoticeLevel === 'ok'
					? 'color: var(--ok); margin-top: 8px;'
					: 'margin-top: 8px;'}
		>
			{compareNotice}
		</p>
	{/if}
	<details class="compare-advanced" style="margin-top: 10px;">
		<summary>{tx('手動で選び直す（上級者向け）', 'Manual selection (advanced)')}</summary>
		<div class="compare-controls" style="margin-top: 10px;">
			<label class="compare-select-group">
				<span class="eyebrow">{tx('左（新しい結果）', 'Left (newer)')}</span>
				<select bind:value={leftId} class="compare-select">
					<option value="">{tx('左側アイテム', 'Left item')}</option>
					{#each data.history as item}
						<option value={item.id} disabled={item.id === rightId}
							>{compareOptionLabel(item)}</option
						>
					{/each}
				</select>
			</label>
			<label class="compare-select-group">
				<span class="eyebrow">{tx('右（比較対象）', 'Right (baseline)')}</span>
				<select bind:value={rightId} class="compare-select">
					<option value="">{tx('右側アイテム', 'Right item')}</option>
					{#each data.history as item}
						<option value={item.id} disabled={item.id === leftId}
							>{compareOptionLabel(item)}</option
						>
					{/each}
				</select>
			</label>
		</div>
		<div class="actions" style="margin-top: 8px;">
			<button class="btn-ghost" onclick={selectLatestSameArtifactPair}>
				{tx('同じArtifactの新旧を選択', 'Select same artifact newer/older')}
			</button>
			<button class="btn-ghost" onclick={swapCompareSides}>
				{tx('左右を入れ替える', 'Swap left and right')}
			</button>
		</div>
	</details>
		<p class="muted" style="margin-top: 8px;">
			{tx(
				'左右で同じ項目は選べません（同一項目は自動で選択不可になります）。',
				'You cannot choose the same item for both sides (same item is disabled automatically).'
			)}
		</p>
		<div class="card-grid compare-meta-grid" style="margin-top: 10px;">
		<article class="panel pipeline-card" style="padding: 10px;">
			<p class="eyebrow">{tx('左側（新）', 'Left (newer)')}</p>
			<div class="path">{leftItem ? leftItem.artifactPath : '-'}</div>
			<p class="muted" style="margin-top: 6px;">
				{leftItem
					? `${dt(leftItem.capturedAt || leftItem.modifiedAt)} / ${leftItem.status}`
					: tx('未選択', 'Not selected')}
			</p>
		</article>
		<article class="panel pipeline-card" style="padding: 10px;">
			<p class="eyebrow">{tx('右側（比較対象）', 'Right (baseline)')}</p>
			<div class="path">{rightItem ? rightItem.artifactPath : '-'}</div>
			<p class="muted" style="margin-top: 6px;">
				{rightItem
					? `${dt(rightItem.capturedAt || rightItem.modifiedAt)} / ${rightItem.status}`
					: tx('未選択', 'Not selected')}
			</p>
		</article>
	</div>
		{#if compareError}
			<p class="muted" style="color: var(--fail); margin-top: 10px;">{compareError}</p>
		{/if}
		{#if compareTone}
			<div
				class="compare-tone-banner"
				class:compare-result-pass={compareTone === 'PASS'}
				class:compare-result-warn={compareTone === 'WARN'}
				class:compare-result-fail={compareTone === 'FAIL'}
			>
				<span class="metric-label">{tx('比較判定', 'Compare Result')}</span>
				<span class={statusClass(compareTone)}>{compareTone}</span>
			</div>
		{/if}
		{#if leftItem && rightItem}
		<div class="metric-row" style="margin-top: 10px;">
			<span class="metric-label">{tx('同一Artifactか', 'Artifact Same')}</span>
			<span class="metric-value"
				>{leftItem.artifactPath === rightItem.artifactPath ? 'YES' : 'NO'}</span
			>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('ステータス差分', 'Status Delta')}</span>
			<span class="metric-value">{leftItem.status} -> {rightItem.status}</span>
		</div>
		<div class="metric-row">
			<span class="metric-label">{tx('取得時刻差分', 'Captured Delta')}</span>
			<span class="metric-value"
				>{dt(leftItem.capturedAt || leftItem.modifiedAt)} -> {dt(
					rightItem.capturedAt || rightItem.modifiedAt
				)}</span
			>
			</div>
		{/if}
			{#if diffSummary}
				<article
					class="panel pipeline-card compare-result-card"
					class:compare-result-pass={compareTone === 'PASS'}
					class:compare-result-warn={compareTone === 'WARN'}
					class:compare-result-fail={compareTone === 'FAIL'}
					style="margin-top: 10px;"
				>
					<p class="eyebrow">{tx('変更キー（短い要約）', 'Changed Keys (short summary)')}</p>
				<p class="muted" style="margin-top: 6px;">
					{tx(
						'上位4件のみ表示します。詳細は下のJSON全文で確認できます。',
						'Shows top 4 keys per type. See full JSON below for details.'
					)}
				</p>
				<div class="metric-row" style="margin-top: 8px;">
					<span class="metric-label">{tx('追加キー', 'Added keys')}</span>
					<span class="metric-value">{diffSummary.addedCount}</span>
				</div>
				<div class="metric-row">
					<span class="metric-label">{tx('削除キー', 'Removed keys')}</span>
					<span class="metric-value">{diffSummary.removedCount}</span>
				</div>
				<div class="metric-row">
					<span class="metric-label">{tx('変更キー', 'Changed keys')}</span>
					<span class="metric-value">{diffSummary.changedCount}</span>
				</div>
				<div class="diff-highlight-grid" style="margin-top: 10px;">
					<section class="panel pipeline-card" style="padding: 10px;">
						<p class="eyebrow">{tx('追加（先頭4）', 'Added (top 4)')}</p>
						{#if diffHighlights.added.length === 0}
							<p class="muted">{tx('なし', 'none')}</p>
						{:else}
							<ul class="diff-highlight-list">
								{#each diffHighlights.added as item}
									<li class="diff-highlight-item">
										<div class="path">{item.path}</div>
										<div class="muted">R: {item.right}</div>
									</li>
								{/each}
							</ul>
						{/if}
					</section>
					<section class="panel pipeline-card" style="padding: 10px;">
						<p class="eyebrow">{tx('削除（先頭4）', 'Removed (top 4)')}</p>
						{#if diffHighlights.removed.length === 0}
							<p class="muted">{tx('なし', 'none')}</p>
						{:else}
							<ul class="diff-highlight-list">
								{#each diffHighlights.removed as item}
									<li class="diff-highlight-item">
										<div class="path">{item.path}</div>
										<div class="muted">L: {item.left}</div>
									</li>
								{/each}
							</ul>
						{/if}
					</section>
					<section class="panel pipeline-card" style="padding: 10px;">
						<p class="eyebrow">{tx('変更（先頭4）', 'Changed (top 4)')}</p>
						{#if diffHighlights.changed.length === 0}
							<p class="muted">{tx('なし', 'none')}</p>
						{:else}
							<ul class="diff-highlight-list">
								{#each diffHighlights.changed as item}
									<li class="diff-highlight-item">
										<div class="path">{item.path}</div>
										<div class="muted">L: {item.left}</div>
										<div class="muted">R: {item.right}</div>
									</li>
								{/each}
							</ul>
						{/if}
					</section>
				</div>
			</article>
		{/if}
	{#if leftPayload !== null && rightPayload !== null}
		<div class="card-grid compare-json-grid" style="margin-top: 12px;">
			<article class="panel pipeline-card">
				<div class="pipeline-head">
					<h3 class="pipeline-title">{tx('左側 JSON', 'Left JSON')}</h3>
					{#if leftItem}
						<span class={statusClass(leftItem.status)}>{leftItem.status}</span>
					{/if}
				</div>
				<div class="path">{leftItem?.artifactPath}</div>
				<div class="log-box compare-json-box">{prettyJson(leftPayload)}</div>
			</article>
			<article class="panel pipeline-card">
				<div class="pipeline-head">
					<h3 class="pipeline-title">{tx('右側 JSON', 'Right JSON')}</h3>
					{#if rightItem}
						<span class={statusClass(rightItem.status)}>{rightItem.status}</span>
					{/if}
				</div>
				<div class="path">{rightItem?.artifactPath}</div>
				<div class="log-box compare-json-box">{prettyJson(rightPayload)}</div>
			</article>
		</div>
	{/if}
</section>

<section class="panel">
	<p class="muted" style="margin-top: 0;">
		{filtered.length}
		{tx('件', 'items')}
	</p>
	<div class="table-wrap">
		<table class="data-table">
				<thead>
					<tr>
						<th>{tx('ソース', 'Source')}</th>
						<th>{tx('ステータス', 'Status')}</th>
						<th>{tx('取得時刻', 'Captured At')}</th>
						<th>{tx('スキーマ', 'Schema')}</th>
						<th>{tx('Artifact', 'Artifact')}</th>
						<th>{tx('要約', 'Summary')}</th>
						<th>{tx('操作', 'Action')}</th>
					</tr>
				</thead>
				<tbody>
					{#each filtered as item}
					<tr>
						<td>{sourceLabel(item.source)}</td>
						<td><span class={statusClass(item.status)}>{item.status}</span></td>
						<td>{dt(item.capturedAt)}</td>
						<td>{item.schema}</td>
						<td class="path">
							{#if item.inspectHref}
								<a class="btn-link" href={item.inspectHref}>{item.artifactPath}</a>
							{:else}
								{item.artifactPath}
							{/if}
						</td>
							<td>
								{item.summary}
							{#if item.inspectHref}
								<div class="muted" style="margin-top: 4px;">
									{tx('詳細は', 'Details in')}
									<a class="btn-link" href={item.inspectHref}
										>{sourceLabel(item.source)}</a
									>
									</div>
								{/if}
							</td>
							<td>
								{#if item.source === 'EVIDENCE'}
									<button
										class="btn-ghost row-compare-btn"
										disabled={compareRunning}
										onclick={() => void quickCompareFromRow(item)}
									>
										{tx('この2件で比較', 'Compare this pair')}
									</button>
								{:else}
									<span class="muted">-</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
	</div>
</section>

<style>
	.compare-controls {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 10px;
		align-items: end;
	}

	.compare-quick-flow {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.compare-advanced summary {
		cursor: pointer;
		font-weight: 700;
	}

	.compare-tone-banner {
		margin-top: 10px;
		padding: 10px 12px;
		border-radius: 12px;
		border: 1px solid var(--line);
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}

	.compare-select-group {
		min-width: 0;
		display: grid;
		gap: 6px;
	}

	.compare-select {
		width: 100%;
		max-width: 100%;
		padding: 10px 12px;
		border-radius: 12px;
		border: 1px solid var(--line);
		font: inherit;
	}

	.compare-meta-grid,
	.compare-json-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
		width: 100%;
	}

	.compare-meta-grid .pipeline-card,
	.compare-json-grid .pipeline-card {
		width: 100%;
		min-width: 0;
	}

	.compare-json-box {
		max-height: 720px;
		overflow-y: auto;
		overflow-x: hidden;
		overflow-wrap: anywhere;
		word-break: break-word;
	}

	.compare-result-card {
		border: 1px solid var(--line);
	}

	.compare-result-pass {
		border-color: color-mix(in srgb, var(--ok) 60%, var(--line));
		background: color-mix(in srgb, var(--ok) 8%, white);
	}

	.compare-result-warn {
		border-color: color-mix(in srgb, var(--warn) 60%, var(--line));
		background: color-mix(in srgb, var(--warn) 8%, white);
	}

	.compare-result-fail {
		border-color: color-mix(in srgb, var(--fail) 60%, var(--line));
		background: color-mix(in srgb, var(--fail) 8%, white);
	}

	.diff-highlight-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 10px;
	}

	.diff-highlight-list {
		margin: 8px 0 0;
		padding-left: 18px;
	}

	.diff-highlight-item {
		margin-bottom: 8px;
	}

	.row-compare-btn {
		padding: 6px 10px;
		white-space: nowrap;
	}

	@media (max-width: 980px) {
		.compare-controls {
			grid-template-columns: 1fr;
		}

		.compare-meta-grid,
		.compare-json-grid,
		.diff-highlight-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
