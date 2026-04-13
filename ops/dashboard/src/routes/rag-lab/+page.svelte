<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { AiLabRunResponse, PipelineSnapshot } from '$lib/server/types';

	type GuideStatus = 'PASS' | 'WARN' | 'FAIL';

	interface RagLabGuideCheck {
		id: 'llm' | 'data' | 'index';
		status: GuideStatus;
		detail: string;
		hint: string;
	}

	interface RagLabGuidePayload {
		apiBase: string;
		model: string;
		checks: RagLabGuideCheck[];
		dataRawPath: string;
		dataRawFileCount: number;
		indexDbPath: string;
		indexDbExists: boolean;
		indexDbSizeBytes: number;
		sampleNoteExists: boolean;
		readyToAsk: boolean;
	}

	interface RagReadonlyFileEntry {
		path: string;
		sizeBytes: number;
		modifiedAt: string;
		preview: string;
	}

	interface RagReadonlySnapshotPayload {
		generatedAt: string;
		dataRoot: string;
		totalFiles: number;
		files: RagReadonlyFileEntry[];
		indexDbPath: string;
		indexDbExists: boolean;
		indexDbSizeBytes: number;
	}

	interface RagModelListPayload {
		apiBase: string;
		selectedModel: string;
		models: string[];
		resolvedEndpoint: string | null;
		error: string | null;
	}

	interface RagDataWriteResponse {
		status: 'PASS' | 'FAIL';
		savedPath: string;
		savedBytes: number;
		rebuild: {
			ran: boolean;
			status: 'PASS' | 'FAIL';
			log: string;
		};
		snapshot: RagReadonlySnapshotPayload;
	}

	interface QuestionPreset {
		id: string;
		labelJa: string;
		labelEn: string;
		questionJa: string;
		questionEn: string;
	}

	interface PageData {
		rag: PipelineSnapshot | null;
		ragConfigPreview: string;
		guide: RagLabGuidePayload;
		snapshot: RagReadonlySnapshotPayload;
		models: RagModelListPayload;
	}

	type ActionTraceStatus = 'RUNNING' | 'PASS' | 'FAIL';

	interface ActionTrace {
		id: string;
		title: string;
		requestedAt: string;
		status: ActionTraceStatus;
		description: string;
		flow: string[];
		result: string;
	}

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	const questionJa = 'hello.md に書かれている合格条件を教えてください。';
	const questionEn = 'What pass condition is written in hello.md?';
	const questionPresets: QuestionPreset[] = [
		{
			id: 'hello-pass-condition',
			labelJa: 'hello: 合格条件',
			labelEn: 'hello: pass condition',
			questionJa: 'hello.md に書かれている合格条件を教えてください。',
			questionEn: 'What pass condition is written in hello.md?'
		},
		{
			id: 'sample-banana',
			labelJa: 'sample_note: 価格質問',
			labelEn: 'sample_note: price question',
			questionJa: 'sample_note.md のバナナ価格を教えてください。',
			questionEn: 'What is the banana price in sample_note.md?'
		},
		{
			id: 'sample-keywords',
			labelJa: 'sample_note: キーワード抽出',
			labelEn: 'sample_note: extract keywords',
			questionJa: 'sample_note.md のキーワードを3つ挙げてください。',
			questionEn: 'List three keywords from sample_note.md.'
		}
	];

	let { data }: { data: PageData } = $props();
	let ragOverride = $state<PipelineSnapshot | null | undefined>(undefined);
	let guideOverride = $state<RagLabGuidePayload | null | undefined>(undefined);
	let snapshotOverride = $state<RagReadonlySnapshotPayload | null | undefined>(undefined);
	let modelCatalogOverride = $state<RagModelListPayload | undefined>(undefined);
	let question = $state(questionJa);
	let running = $state(false);
	let checkingGuide = $state(false);
	let refreshingSnapshot = $state(false);
	let refreshingModels = $state(false);
	let error = $state('');
	let latestLog = $state('');
	let latestStatus = $state('');
	let previousLog = $state('');
	let previousStatus = $state('');
	let activeTipId = $state('');
	let lastAction = $state<ActionTrace | null>(null);
	let simpleView = $state(true);
	let selectedModel = $state('');
	let newDataFileName = $state('note_new.md');
	let newDataContent = $state('');
	let savingData = $state(false);
	let saveDataMessage = $state('');
	let saveDataStatus = $state<'PASS' | 'FAIL' | ''>('');
	let saveDataLog = $state('');
	let hasRagTuningRun = $state(false);
	let selectedMode = $state<'guided' | 'expert'>('guided');
	let skipTutorial = $state(false);
	let selectedPhase = $state<1 | 2 | 3 | 4>(1);
	let lastLocale = $state(localeState.value);
	const rag = $derived<PipelineSnapshot | null>(
		ragOverride === undefined ? data.rag : ragOverride
	);
	const guide = $derived<RagLabGuidePayload | null>(
		guideOverride === undefined ? data.guide : guideOverride
	);
	const snapshot = $derived<RagReadonlySnapshotPayload | null>(
		snapshotOverride === undefined ? data.snapshot : snapshotOverride
	);
	const modelCatalog = $derived<RagModelListPayload>(
		modelCatalogOverride === undefined ? data.models : modelCatalogOverride
	);
	const mode = $derived<'guided' | 'expert'>(skipTutorial ? 'expert' : selectedMode);
	$effect(() => {
		const nextRag = data.rag;
		const nextGuide = data.guide;
		const nextSnapshot = data.snapshot;
		const nextModels = data.models;
		if (nextRag || nextGuide || nextSnapshot || nextModels) {
			// Reset local overrides when server-provided page data changes.
		}
		ragOverride = undefined;
		guideOverride = undefined;
		snapshotOverride = undefined;
		modelCatalogOverride = undefined;
	});
	$effect(() => {
		const previousDefault = lastLocale === 'ja' ? questionJa : questionEn;
		const nextDefault = localeState.value === 'ja' ? questionJa : questionEn;
		if (question === previousDefault) {
			question = nextDefault;
		}
		lastLocale = localeState.value;
	});
	$effect(() => {
		const candidate = (modelCatalog.selectedModel || '').trim();
		if (candidate && !selectedModel.trim()) {
			selectedModel = candidate;
		}
	});
	$effect(() => {
		if (modelCatalog.models.length > 0 && !modelCatalog.models.includes(selectedModel)) {
			selectedModel = modelCatalog.models[0];
		}
	});

	function statusClass(status: string): string {
		return `status-pill status-${status.toLowerCase()}`;
	}

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	interface TutorialPhase {
		id: 1 | 2 | 3 | 4;
		titleJa: string;
		titleEn: string;
		goalJa: string;
		goalEn: string;
	}

	const tutorialPhases: TutorialPhase[] = [
		{
			id: 1,
			titleJa: '環境チェック',
			titleEn: 'Environment Check',
			goalJa: 'LLM / data / index が使えることを確認',
			goalEn: 'Confirm LLM / data / index readiness'
		},
		{
			id: 2,
			titleJa: 'サンプル実行',
			titleEn: 'Sample Run',
			goalJa: 'hello.md への質問で最初の回答を得る',
			goalEn: 'Get first answer with hello.md question'
		},
		{
			id: 3,
			titleJa: '結果読解',
			titleEn: 'Read Result',
			goalJa: '結論・根拠・参照の見方を理解',
			goalEn: 'Understand conclusion/evidence/reference'
		},
		{
			id: 4,
			titleJa: '調整と比較',
			titleEn: 'Tune and Compare',
			goalJa: 'RAG調整を走らせて指標差分を確認',
			goalEn: 'Run tuning and inspect metric deltas'
		}
	];

	function selectMode(nextMode: 'guided' | 'expert'): void {
		selectedMode = nextMode;
		skipTutorial = nextMode === 'expert';
	}

	function phaseTitle(phase: TutorialPhase): string {
		return localeState.value === 'ja' ? phase.titleJa : phase.titleEn;
	}

	function phaseGoal(phase: TutorialPhase): string {
		return localeState.value === 'ja' ? phase.goalJa : phase.goalEn;
	}

	function phaseDone(phaseId: 1 | 2 | 3 | 4): boolean {
		switch (phaseId) {
			case 1:
				return Boolean(guide?.readyToAsk);
			case 2:
				return latestStatus.toUpperCase() === 'PASS' && latestLog.length > 0;
			case 3:
				return latestLog.length > 0;
			case 4:
				return hasRagTuningRun;
			default:
				return false;
		}
	}

	function phaseStatus(phaseId: 1 | 2 | 3 | 4): 'PASS' | 'WARN' {
		return phaseDone(phaseId) ? 'PASS' : 'WARN';
	}

	function phaseActionLabel(phaseId: 1 | 2 | 3 | 4): string {
		switch (phaseId) {
			case 1:
				return tx('このフェーズを実行: 状態を再チェック', 'Run Phase: Recheck status');
			case 2:
				return tx('このフェーズを実行: サンプル質問を実行', 'Run Phase: Sample question');
			case 3:
				return tx('このフェーズを実行: 最新結果を読解', 'Run Phase: Read latest result');
			case 4:
				return tx('このフェーズを実行: RAG調整ループ', 'Run Phase: RAG tuning loop');
			default:
				return tx('フェーズを実行', 'Run phase');
		}
	}

	async function runSelectedPhase(): Promise<void> {
		switch (selectedPhase) {
			case 1:
				await refreshGuide();
				return;
			case 2:
				await runPreset(questionPresets[0]);
				return;
			case 3:
				await askLocalModel(tx('結果読解用の再実行', 'Rerun for result reading'));
				return;
			case 4:
				await runRagTuning();
		}
	}

	function advancePhase(): void {
		if (selectedPhase === 4) {
			return;
		}
		selectedPhase = (selectedPhase + 1) as 1 | 2 | 3 | 4;
	}

	function formatBytes(sizeBytes: number): string {
		if (!Number.isFinite(sizeBytes) || sizeBytes < 1024) {
			return `${Math.max(0, Math.trunc(sizeBytes))} B`;
		}
		if (sizeBytes < 1024 * 1024) {
			return `${(sizeBytes / 1024).toFixed(1)} KB`;
		}
		return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`;
	}

	function formatLocaleDate(iso: string): string {
		const dt = new Date(iso);
		if (Number.isNaN(dt.getTime())) {
			return iso;
		}
		return dt.toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function toggleTip(id: string): void {
		activeTipId = activeTipId === id ? '' : id;
	}

	function isTipOpen(ids: string[]): boolean {
		return ids.includes(activeTipId);
	}

	function tipTitle(id: string): string {
		if (id.startsWith('preset:')) {
			return tx('質問テンプレートの使い方', 'How to use question templates');
		}
		switch (id) {
			case 'check-status':
				return tx('状態を再チェックとは？', 'What is Recheck Status?');
			case 'run-rag-tuning':
				return tx('RAG調整ループを実行とは？', 'What is Run RAG Tuning Loop?');
			case 'refresh-metrics':
				return tx('指標を更新とは？', 'What is Refresh Metrics?');
			case 'ask-local':
				return tx('ローカルモデルに質問とは？', 'What is Ask Local Model?');
			case 'run-sample':
				return tx('サンプル質問を実行とは？', 'What is Run sample question?');
			default:
				return tx('このボタンの説明', 'About this button');
		}
	}

	function tipBody(id: string): string {
		if (id.startsWith('preset:')) {
			const presetId = id.replace('preset:', '');
			const preset = questionPresets.find((item) => item.id === presetId);
			const label = preset
				? presetLabel(preset)
				: tx('質問テンプレート', 'question template');
			return tx(
				`${label}\n\n何をする:\n- 質問欄にテンプレート文を自動入力します（まだ実行しません）。\n\n次にどうする:\n- 入力内容を少し編集して「ローカルモデルに質問」\n- そのまま動かすなら「1クリック: サンプル質問を実行」`,
				`${label}\n\nWhat it does:\n- Auto-fills the question text (does not execute yet).\n\nWhat to do next:\n- Edit the text then click "Ask Local Model"\n- Or run directly with "One-click: Run sample question"`
			);
		}
		switch (id) {
			case 'check-status':
				return tx(
					'何をする:\n- LLM API 接続\n- data/raw の存在と件数\n- index DB の存在\nを確認します。\n\n内部処理:\n- GET /api/dashboard/rag-lab/preflight を実行\n- /models, data/raw, index/index.sqlite3 を検査\n\nいつ使う:\n- 起動直後\n- 設定を変更した直後\n- 「不明 / CONTEXTが空」が出た直後',
					'What it does:\n- Checks LLM API connectivity, data/raw presence, and index DB.\n\nInternal flow:\n- Calls GET /api/dashboard/rag-lab/preflight\n- Verifies /models, data/raw, and index/index.sqlite3\n\nUse when:\n- Right after startup\n- After config changes\n- After unknown/empty-context results'
				);
			case 'run-rag-tuning':
				return tx(
					'何をする:\n- RAG調整スクリプトを実行して、baseline/candidate 指標を更新します。\n\n内部処理:\n- POST /api/dashboard/ai-lab/run { channel: "rag-tuning" }\n- scripts/ops/s25_rag_tuning_loop.py を実行\n\n使いどころ:\n- chunk_size, overlap, top_k を見直した後の比較検証',
					'What it does:\n- Runs RAG tuning script and updates baseline/candidate metrics.\n\nInternal flow:\n- POST /api/dashboard/ai-lab/run { channel: "rag-tuning" }\n- Executes scripts/ops/s25_rag_tuning_loop.py\n\nUse when:\n- After adjusting chunk_size, overlap, or top_k'
				);
			case 'refresh-metrics':
				return tx(
					'何をする:\n- 画面のRAGスナップショット指標だけを再取得します（軽量）。\n\n内部処理:\n- GET /api/dashboard/overview\n\n使いどころ:\n- 調整実行後の最新値確認',
					'What it does:\n- Refreshes only the RAG snapshot metrics (lightweight).\n\nInternal flow:\n- GET /api/dashboard/overview\n\nUse when:\n- Checking latest values after tuning runs'
				);
			case 'ask-local':
				return tx(
					'何をする:\n- 質問文でRAG検索 + ローカルLLM回答を実行します。\n\n内部処理:\n- POST /api/dashboard/ai-lab/run { channel: "local-model", prompt }\n- サーバーで src/ask.py 実行\n- index検索→CONTEXT生成→LLM問い合わせ→参照付き整形\n\n使いどころ:\n- 参照付きで答えられるかの確認',
					'What it does:\n- Runs retrieval + local LLM answer for your prompt.\n\nInternal flow:\n- POST /api/dashboard/ai-lab/run { channel: "local-model", prompt }\n- Executes src/ask.py on server\n- Retrieves evidence, builds context, queries LLM, formats referenced output\n\nUse when:\n- Verifying evidence-grounded responses'
				);
			case 'run-sample':
				return tx(
					'何をする:\n- 用意済みのサンプル質問をそのまま実行します。\n\n内部処理:\n- 質問欄へテンプレート反映\n- 直後に「ローカルモデルに質問」と同じ処理を実行\n\n使いどころ:\n- 初回の動作確認\n- 設定変更後のスモークテスト',
					'What it does:\n- Runs a prepared sample question end-to-end.\n\nInternal flow:\n- Applies template question\n- Immediately runs the same flow as Ask Local Model\n\nUse when:\n- First-run verification\n- Smoke test after config changes'
				);
			default:
				return tx(
					'この操作の説明は準備中です。基本は「押す前に i を開く」で挙動を確認できます。',
					'Description for this action is not ready yet. Open i before clicking to preview behavior.'
				);
		}
	}

	function startActionTrace(input: {
		id: string;
		title: string;
		description: string;
		flow: string[];
	}): void {
		lastAction = {
			id: input.id,
			title: input.title,
			requestedAt: new Date().toISOString(),
			status: 'RUNNING',
			description: input.description,
			flow: input.flow,
			result: tx('実行中です...', 'Running...')
		};
	}

	function finishActionTrace(status: 'PASS' | 'FAIL', result: string): void {
		if (!lastAction) {
			return;
		}
		lastAction = {
			...lastAction,
			status,
			result
		};
	}

	function traceSummary(trace: ActionTrace): string {
		return [
			`${tx('実行内容', 'Action')}: ${trace.title}`,
			`${tx('説明', 'Description')}: ${trace.description}`,
			`${tx('内部フロー', 'Internal flow')}:`,
			...trace.flow.map((item) => `- ${item}`),
			`${tx('結果', 'Result')}: ${trace.result}`
		].join('\n');
	}

	function guideReadyClass(ready: boolean): string {
		return ready
			? 'guide-ready-chip guide-ready-chip-ok'
			: 'guide-ready-chip guide-ready-chip-warn';
	}

	function presetLabel(preset: QuestionPreset): string {
		return localeState.value === 'ja' ? preset.labelJa : preset.labelEn;
	}

	function presetQuestion(preset: QuestionPreset): string {
		return localeState.value === 'ja' ? preset.questionJa : preset.questionEn;
	}

	function applyPreset(preset: QuestionPreset): void {
		question = presetQuestion(preset);
	}

	async function runPreset(preset: QuestionPreset): Promise<void> {
		question = presetQuestion(preset);
		await askLocalModel(tx('サンプル質問を実行', 'Run sample question'));
	}

	function guideTitle(id: RagLabGuideCheck['id']): string {
		switch (id) {
			case 'llm':
				return tx('LLM起動確認', 'LLM readiness');
			case 'data':
				return tx('data存在確認', 'data availability');
			case 'index':
				return tx('index存在確認', 'index availability');
			default:
				return id;
		}
	}

	function guideDetailText(check: RagLabGuideCheck, payload: RagLabGuidePayload): string {
		if (check.id === 'llm') {
			if (check.status === 'PASS') {
				return tx(
					'ローカルLLM APIに接続でき、モデル一覧を取得できました。',
					'Local LLM API is reachable and model list is available.'
				);
			}
			if (check.status === 'WARN') {
				return tx(
					'APIは応答していますが、モデルが見つかりません。モデル読込状態を確認してください。',
					'API is reachable, but no model was reported. Check model loading status.'
				);
			}
			return tx(
				'LLM APIに接続できません。llama-server 起動と API base 設定を確認してください。',
				'LLM API is not reachable. Check llama-server and API base configuration.'
			);
		}
		if (check.id === 'data') {
			if (check.status === 'PASS') {
				return tx(
					`data/raw に ${payload.dataRawFileCount} 件のファイルがあります。`,
					`${payload.dataRawFileCount} file(s) detected under data/raw.`
				);
			}
			if (check.status === 'WARN') {
				return tx(
					'data/raw は存在しますが、参照ファイルがほぼ空です。',
					'data/raw exists, but reference files are nearly empty.'
				);
			}
			return tx(
				'data/raw が見つかりません。参照元ファイルを配置してください。',
				'data/raw is missing. Add source files first.'
			);
		}
		if (check.status === 'PASS') {
			return tx(
				`index DB が見つかりました（約 ${Math.max(1, Math.round(payload.indexDbSizeBytes / 1024))} KB）。`,
				`Index DB is available (${Math.max(1, Math.round(payload.indexDbSizeBytes / 1024))} KB).`
			);
		}
		if (check.status === 'WARN') {
			return tx(
				'index DB はありますが、内容が不十分な可能性があります。',
				'Index DB exists, but content may be insufficient.'
			);
		}
		return tx(
			'index DB が見つかりません。ingest/build_index を実行してください。',
			'Index DB is missing. Run ingest/build_index.'
		);
	}

	function guideNextActionText(check: RagLabGuideCheck, payload: RagLabGuidePayload): string {
		if (check.id === 'llm') {
			return check.status === 'PASS'
				? tx(
						'次はサンプル質問を実行して、参照付き回答が返るか確認します。',
						'Next, run a sample question and verify referenced output.'
					)
				: tx(
						'ターミナルAで llama-server を起動し、`OPENAI_API_BASE` を見直してください。',
						'Start llama-server and verify `OPENAI_API_BASE`.'
					);
		}
		if (check.id === 'data') {
			return check.status === 'PASS'
				? tx(
						'テンプレート質問を押して、どのファイルが参照されるか確認します。',
						'Use template questions to confirm which files are referenced.'
					)
				: tx(
						`まず ${payload.dataRawPath} に参照ファイルを追加してください。`,
						`Add reference files under ${payload.dataRawPath} first.`
					);
		}
		return check.status === 'PASS'
			? tx(
					'準備完了です。ローカル質問または1クリック実行に進んでください。',
					'Setup is ready. Proceed with local question or one-click run.'
				)
			: tx(
					'index を再生成後に「状態を再チェック」を押してください。',
					'Rebuild index, then click recheck.'
				);
	}

	function guideRawText(check: RagLabGuideCheck): string {
		return `${check.detail}\n${tx('サーバー提案', 'Server hint')}: ${check.hint}`;
	}

	function firstBlockingCheck(): RagLabGuideCheck | null {
		if (!guide) {
			return null;
		}
		return guide.checks.find((item) => item.status !== 'PASS') || null;
	}

	function isContextEmpty(log: string): boolean {
		const source = (log || '').toLowerCase();
		return (
			source.includes('contextが空') ||
			source.includes('参照できる根拠が見つかりません') ||
			source.includes('不明（contextが空）')
		);
	}

	function extractReferenceLines(log: string): string[] {
		if (!log) {
			return [];
		}
		const lines = log.split(/\r?\n/);
		const refs: string[] = [];
		let inRefs = false;
		for (const rawLine of lines) {
			const line = rawLine.trim();
			if (!line) {
				if (inRefs) {
					break;
				}
				continue;
			}
			if (line.startsWith('参照:') || line.toLowerCase().startsWith('references:')) {
				inRefs = true;
				continue;
			}
			if (inRefs) {
				if (line.startsWith('- ')) {
					refs.push(line.slice(2).trim());
					continue;
				}
				if (line.endsWith(':')) {
					break;
				}
			}
		}
		return refs.filter((item) => item && item !== '不明（参照なし)' && item !== 'N/A');
	}

	function ragImpactSummaryText(): string {
		if (!latestLog) {
			return tx(
				'まだ比較対象がありません。RAGデータ追加後に「ローカルモデルに質問」を実行してください。',
				'No comparison yet. Run Ask Local Model after adding RAG data.'
			);
		}
		const beforeRefs = extractReferenceLines(previousLog);
		const afterRefs = extractReferenceLines(latestLog);
		const added = afterRefs.filter((ref) => !beforeRefs.includes(ref));
		const removed = beforeRefs.filter((ref) => !afterRefs.includes(ref));
		const beforeContext = previousLog ? !isContextEmpty(previousLog) : false;
		const afterContext = !isContextEmpty(latestLog);

		return [
			`${tx('ステータス変化', 'Status change')}: ${previousStatus || 'N/A'} -> ${latestStatus || 'N/A'}`,
			`${tx('参照件数', 'Reference count')}: ${beforeRefs.length} -> ${afterRefs.length}`,
			`${tx('CONTEXT状態', 'Context state')}: ${beforeContext ? 'OK' : 'EMPTY'} -> ${afterContext ? 'OK' : 'EMPTY'}`,
			`${tx('追加された参照', 'Added references')}: ${added.length > 0 ? added.slice(0, 4).join(', ') : '-'}`,
			`${tx('消えた参照', 'Removed references')}: ${removed.length > 0 ? removed.slice(0, 4).join(', ') : '-'}`
		].join('\n');
	}

	type CoachState = 'idle' | 'success' | 'empty' | 'fail';

	function coachState(): CoachState {
		const status = (latestStatus || '').toUpperCase();
		if (!latestLog && !error) {
			return 'idle';
		}
		if (status === 'FAIL' || error) {
			return 'fail';
		}
		if (latestLog && isContextEmpty(latestLog)) {
			return 'empty';
		}
		return 'success';
	}

	function coachTitle(): string {
		switch (coachState()) {
			case 'success':
				return tx('実験は成功です', 'Experiment succeeded');
			case 'empty':
				return tx('根拠不足で回答が弱い状態です', 'Evidence is insufficient');
			case 'fail':
				return tx('実行でエラーが発生しました', 'Execution failed');
			default:
				return tx('まず1回動かしてみましょう', 'Run one action to start');
		}
	}

	function coachNarrative(): string {
		switch (coachState()) {
			case 'success':
				return tx(
					'質問に対してRAG検索がヒットし、根拠付きの応答フローが完了しています。この状態を基準に、質問や調整値を1つずつ変えて比較するのが最短です。',
					'Retrieval matched evidence and the response flow completed. Use this as a baseline and change one variable at a time.'
				);
			case 'empty':
				return tx(
					'システムは動いていますが、質問に対応する根拠が見つからない状態です。質問の具体化か、data/raw・index の強化が必要です。',
					'The system is running, but no matching evidence was found. Make the question more specific or improve data/raw and index.'
				);
			case 'fail':
				return tx(
					'API接続やモデル起動、パス設定のいずれかで止まっています。実行トレースを見て、最初の失敗地点を1つずつ解消します。',
					'Execution stopped due to API/model/path issues. Inspect the trace and resolve the first failing point.'
				);
			default:
				return tx(
					'このページは「押して結果を見る」ことで理解が進む設計です。まずSTEP1を押して、最新出力と実行トレースを見てください。',
					'This page is designed for learning by running. Start with STEP1, then read Latest Output and Execution Trace.'
				);
		}
	}

	function coachNextMoves(): string {
		switch (coachState()) {
			case 'success':
				return tx(
					'次にやること:\n1) STEP2で質問を別テーマに変える\n2) 参照ファイル名と結論の整合を確認\n3) STEP3で tuning 実行後、指標差分を記録',
					'Next moves:\n1) Use STEP2 with a different question\n2) Verify file references and conclusions align\n3) Run STEP3 tuning and record metric deltas'
				);
			case 'empty':
				return tx(
					'次にやること:\n1) sample/hello のテンプレ質問を実行\n2) data/raw と index の状態を再チェック\n3) 質問文にファイル名や固有語を追加',
					'Next moves:\n1) Run sample/hello template question\n2) Recheck data/raw and index\n3) Add file names or concrete keywords to the question'
				);
			case 'fail':
				return tx(
					'次にやること:\n1) 状態を再チェック\n2) OPENAI_API_BASE と llama-server を確認\n3) 失敗ログを修正後に再実行',
					'Next moves:\n1) Recheck status\n2) Verify OPENAI_API_BASE and llama-server\n3) Fix the failing log point and rerun'
				);
			default:
				return tx(
					'次にやること:\n1) STEP1を実行\n2) Latest Output を読む\n3) 実行トレースで内部処理を確認',
					'Next moves:\n1) Run STEP1\n2) Read Latest Output\n3) Inspect internal flow in Execution Trace'
				);
		}
	}

	function finalOutcomeSummary(): string {
		const completed = tutorialPhases.filter((phase) => phaseDone(phase.id)).length;
		const latest = latestStatus || tx('未実行', 'Not run yet');
		const contextState = latestLog
			? isContextEmpty(latestLog)
				? tx('CONTEXT不足', 'Context missing')
				: tx('CONTEXTあり', 'Context present')
			: tx('未確認', 'Not checked');
		const ragHeadline =
			rag?.metrics
				.slice(0, 2)
				.map((metric) => `${metric.label}: ${metric.value}`)
				.join(' / ') || tx('指標なし', 'No metrics');
		return [
			`${tx('現在モード', 'Current mode')}: ${
				mode === 'guided' ? tx('ガイド', 'Guided') : tx('上級', 'Expert')
			}`,
			`${tx('フェーズ進捗', 'Phase progress')}: ${completed}/${tutorialPhases.length}`,
			`${tx('環境状態', 'Environment')}: ${
				guide?.readyToAsk ? tx('質問可能', 'Ready to ask') : tx('要確認', 'Needs checks')
			}`,
			`${tx('最新実行', 'Latest execution')}: ${latest}`,
			`${tx('回答コンテキスト', 'Answer context')}: ${contextState}`,
			`${tx('RAGスナップショット', 'RAG snapshot')}: ${ragHeadline}`
		].join('\n');
	}

	function snapshotSummaryText(payload: RagReadonlySnapshotPayload): string {
		return [
			`${tx('生成時刻', 'Generated at')}: ${formatLocaleDate(payload.generatedAt)}`,
			`data root: ${payload.dataRoot} (${payload.totalFiles} files)`,
			`index: ${payload.indexDbPath} (${payload.indexDbExists ? 'exists' : 'missing'} / ${formatBytes(payload.indexDbSizeBytes)})`
		].join('\n');
	}

	function modelRuntimeSummary(): string {
		return [
			`${tx('現在選択モデル', 'Selected model')}: ${selectedModel}`,
			`${tx('API base', 'API base')}: ${modelCatalog.apiBase}`
		].join('\n');
	}

	async function refreshReadonlySnapshot() {
		startActionTrace({
			id: 'refresh-readonly-data',
			title: tx('RAGデータ実体を更新', 'Refresh read-only RAG data'),
			description: tx(
				'data/raw と index のREAD-ONLYスナップショットを再取得します。',
				'Reloads read-only snapshot for data/raw and index.'
			),
			flow: ['GET /api/dashboard/rag-lab/snapshot']
		});
		refreshingSnapshot = true;
		try {
			const res = await fetch('/api/dashboard/rag-lab/snapshot');
			if (!res.ok) {
				finishActionTrace(
					'FAIL',
					tx('READ-ONLYデータの更新に失敗しました。', 'Failed to refresh read-only data.')
				);
				return;
			}
			snapshotOverride = (await res.json()) as RagReadonlySnapshotPayload;
			finishActionTrace(
				'PASS',
				tx('RAGデータ実体を更新しました。', 'Read-only RAG data was refreshed.')
			);
		} catch (e) {
			const text =
				e instanceof Error
					? e.message
					: tx('READ-ONLYデータ更新に失敗しました。', 'Snapshot refresh failed.');
			finishActionTrace('FAIL', text);
		} finally {
			refreshingSnapshot = false;
		}
	}

	async function refreshModelList() {
		startActionTrace({
			id: 'refresh-model-list',
			title: tx('モデル一覧を更新', 'Refresh model list'),
			description: tx(
				'OpenAI互換エンドポイントから利用可能モデルを再取得します。',
				'Reloads available models from OpenAI-compatible endpoint.'
			),
			flow: ['GET /api/dashboard/rag-lab/models']
		});
		refreshingModels = true;
		try {
			const res = await fetch('/api/dashboard/rag-lab/models');
			if (!res.ok) {
				finishActionTrace(
					'FAIL',
					tx('モデル一覧更新に失敗しました。', 'Failed to refresh models.')
				);
				return;
			}
			const payload = (await res.json()) as RagModelListPayload;
			modelCatalogOverride = payload;
			if (!selectedModel.trim()) {
				selectedModel = payload.selectedModel || '';
			}
			finishActionTrace(
				'PASS',
				tx('モデル一覧を更新しました。', 'Model list was refreshed.')
			);
		} catch (e) {
			const text =
				e instanceof Error
					? e.message
					: tx('モデル一覧更新に失敗しました。', 'Failed to refresh models.');
			finishActionTrace('FAIL', text);
		} finally {
			refreshingModels = false;
		}
	}

	async function addRagData() {
		startActionTrace({
			id: 'add-rag-data',
			title: tx('RAGデータを追加', 'Add RAG data'),
			description: tx(
				'data/raw にMarkdownを追加して、indexを再構築します。',
				'Adds markdown to data/raw and rebuilds index.'
			),
			flow: [
				'POST /api/dashboard/rag-lab/data',
				'write data/raw/*.md',
				'python src/build_index.py'
			]
		});
		savingData = true;
		saveDataMessage = '';
		saveDataStatus = '';
		saveDataLog = '';
		try {
			const res = await fetch('/api/dashboard/rag-lab/data', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					fileName: newDataFileName,
					content: newDataContent,
					rebuildIndex: true
				})
			});
			const payload = (await res.json()) as RagDataWriteResponse & { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error || tx('データ追加に失敗しました。', 'Failed to add data.')
				);
			}
			snapshotOverride = payload.snapshot;
			saveDataStatus = payload.status;
			saveDataMessage = tx(
				`保存: ${payload.savedPath} (${formatBytes(payload.savedBytes)})`,
				`Saved: ${payload.savedPath} (${formatBytes(payload.savedBytes)})`
			);
			saveDataLog = payload.rebuild.log;
			finishActionTrace(
				payload.status === 'PASS' ? 'PASS' : 'FAIL',
				payload.status === 'PASS'
					? tx('追加とindex更新が完了しました。', 'Data add and index rebuild completed.')
					: tx(
							'追加は成功、index更新で失敗しました。',
							'Data saved, but index rebuild failed.'
						)
			);
			await refreshGuide();
		} catch (e) {
			const text =
				e instanceof Error
					? e.message
					: tx('RAGデータ追加に失敗しました。', 'Failed to add RAG data.');
			saveDataStatus = 'FAIL';
			saveDataMessage = text;
			finishActionTrace('FAIL', text);
		} finally {
			savingData = false;
		}
	}

	function guideSummaryText(payload: RagLabGuidePayload): string {
		return [
			`${tx('現在のAPI base', 'Current API base')}: ${payload.apiBase}`,
			`${tx('現在のモデル', 'Current model')}: ${payload.model}`,
			`data/raw: ${payload.dataRawPath} (${payload.dataRawFileCount} files)`,
			`index DB: ${payload.indexDbPath} (${payload.indexDbExists ? 'exists' : 'missing'})`
		].join('\n');
	}

	function emptyContextSummaryText(payload: RagLabGuidePayload): string {
		return [
			`- data/raw files: ${payload.dataRawFileCount}`,
			`- sample_note.md: ${payload.sampleNoteExists ? 'found' : 'missing'}`,
			`- index DB: ${payload.indexDbExists ? 'found' : 'missing'} (${payload.indexDbPath})`
		].join('\n');
	}

	async function refreshGuide() {
		startActionTrace({
			id: 'check-status',
			title: tx('状態を再チェック', 'Recheck Status'),
			description: tx(
				'LLM / data / index の接続状態を確認します。',
				'Checks readiness of LLM, data, and index.'
			),
			flow: ['GET /api/dashboard/rag-lab/preflight', '/models, data/raw, index/index.sqlite3']
		});
		checkingGuide = true;
		try {
			const res = await fetch('/api/dashboard/rag-lab/preflight');
			if (!res.ok) {
				finishActionTrace(
					'FAIL',
					tx('状態確認APIがエラーを返しました。', 'Preflight API returned an error.')
				);
				return;
			}
			guideOverride = (await res.json()) as RagLabGuidePayload;
			finishActionTrace(
				'PASS',
				tx(
					'状態確認が完了し、最新チェック結果を取得しました。',
					'Preflight checks completed.'
				)
			);
		} catch (e) {
			const text =
				e instanceof Error
					? e.message
					: tx('状態確認に失敗しました。', 'Failed to recheck status.');
			finishActionTrace('FAIL', text);
		} finally {
			checkingGuide = false;
		}
	}

	async function refreshOverview() {
		startActionTrace({
			id: 'refresh-metrics',
			title: tx('指標を更新', 'Refresh Metrics'),
			description: tx(
				'画面のRAGスナップショット指標を再取得します。',
				'Reloads RAG snapshot metrics for this page.'
			),
			flow: ['GET /api/dashboard/overview']
		});
		const res = await fetch('/api/dashboard/overview');
		if (!res.ok) {
			finishActionTrace('FAIL', tx('指標の取得に失敗しました。', 'Failed to fetch metrics.'));
			return;
		}
		const payload = (await res.json()) as { pipelines: PipelineSnapshot[] };
		ragOverride = payload.pipelines.find((row) => row.key === 'rag') || null;
		finishActionTrace(
			'PASS',
			tx('指標を更新しました。', 'Metrics were refreshed successfully.')
		);
	}

	async function runRagTuning() {
		startActionTrace({
			id: 'run-rag-tuning',
			title: tx('RAG調整ループを実行', 'Run RAG Tuning Loop'),
			description: tx(
				'調整ループを実行して比較指標を更新します。',
				'Runs tuning loop and updates comparison metrics.'
			),
			flow: [
				'POST /api/dashboard/ai-lab/run',
				'channel=rag-tuning',
				'scripts/ops/s25_rag_tuning_loop.py'
			]
		});
		running = true;
		error = '';
		latestLog = '';
		try {
			const res = await fetch('/api/dashboard/ai-lab/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ channel: 'rag-tuning' })
			});
			const payload = (await res.json()) as AiLabRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(payload.error || tx('RAG調整に失敗しました', 'rag tuning failed'));
			}
			latestStatus = payload.record.status;
			latestLog = payload.record.stdout;
			hasRagTuningRun = true;
			finishActionTrace(
				'PASS',
				tx('RAG調整ループを実行し、ログを取得しました。', 'RAG tuning loop completed.')
			);
			await refreshOverview();
		} catch (e) {
			error =
				e instanceof Error ? e.message : tx('RAG調整に失敗しました', 'rag tuning failed');
			finishActionTrace('FAIL', error);
		} finally {
			running = false;
		}
	}

	async function askLocalModel(
		label = tx('ローカルモデルに質問', 'Ask Local Model'),
		modelName = selectedModel
	) {
		startActionTrace({
			id: 'ask-local',
			title: label,
			description: tx(
				'質問文でRAG検索とローカルLLM回答を実行します。',
				'Runs retrieval and local LLM answering for your prompt.'
			),
			flow: [
				'POST /api/dashboard/ai-lab/run',
				'channel=local-model',
				'src/ask.py',
				'index search -> context build -> llm call'
			]
		});
		running = true;
		error = '';
		previousLog = latestLog;
		previousStatus = latestStatus;
		latestLog = '';
		try {
			const res = await fetch('/api/dashboard/ai-lab/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ channel: 'local-model', prompt: question, model: modelName })
			});
			const payload = (await res.json()) as AiLabRunResponse & { error?: string };
			if (!res.ok) {
				throw new Error(
					payload.error ||
						tx('ローカルモデル問い合わせに失敗しました', 'local model query failed')
				);
			}
			latestStatus = payload.record.status;
			latestLog = payload.record.stdout || payload.record.stderr;
			finishActionTrace(
				'PASS',
				tx(
					'ローカル質問を実行し、最新出力に結果を反映しました。',
					'Local question executed and latest output was updated.'
				)
			);
			await refreshGuide();
		} catch (e) {
			error = e instanceof Error ? e.message : tx('問い合わせに失敗しました', 'query failed');
			finishActionTrace('FAIL', error);
		} finally {
			running = false;
		}
	}
</script>

<section class="panel panel-strong" style="margin-bottom: 14px;">
	<p class="eyebrow">Simple RAG</p>
	<h1 class="title">{tx('RAGデータ一覧 + 追加 + 実行結果', 'RAG List + Add + Result')}</h1>
	<p class="muted">
		{tx(
			'この画面はシンプル表示です。RAGデータを追加し、モデルを選んで結果を確認できます。',
			'This simple view lets you add RAG data, choose a model, and check results.'
		)}
	</p>
	<label class="mode-toggle" style="margin-top: 12px;">
		<input type="checkbox" bind:checked={simpleView} />
		<span>{tx('シンプル表示（推奨）', 'Simple view (recommended)')}</span>
	</label>
</section>

{#if simpleView}
	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">Data</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('実際のRAGデータ一覧（READ ONLY）', 'Actual RAG Data List (READ ONLY)')}
		</h2>
		{#if snapshot}
			<div class="snippet" style="margin-top: 10px;">{snapshotSummaryText(snapshot)}</div>
			<div class="table-wrap">
				<table class="data-table">
					<thead>
						<tr>
							<th>{tx('ファイル', 'File')}</th>
							<th>{tx('サイズ', 'Size')}</th>
							<th>{tx('更新', 'Updated')}</th>
							<th>{tx('プレビュー', 'Preview')}</th>
						</tr>
					</thead>
					<tbody>
						{#if snapshot.files.length === 0}
							<tr>
								<td colspan="4"
									>{tx(
										'表示できるファイルがありません。',
										'No files available.'
									)}</td
								>
							</tr>
						{:else}
							{#each snapshot.files as file}
								<tr>
									<td class="path">{file.path}</td>
									<td>{formatBytes(file.sizeBytes)}</td>
									<td>{formatLocaleDate(file.modifiedAt)}</td>
									<td class="readonly-preview">{file.preview}</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		{/if}
		<div class="actions" style="margin-top: 10px;">
			<button
				class="btn-ghost"
				disabled={refreshingSnapshot}
				onclick={refreshReadonlySnapshot}
				>{refreshingSnapshot
					? tx('更新中...', 'Refreshing...')
					: tx('一覧を更新', 'Refresh list')}</button
			>
		</div>
	</section>

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">Add Data</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('RAGデータを追加', 'Add RAG Data')}
		</h2>
		<label style="display: grid; gap: 6px; margin-top: 10px;">
			<span class="eyebrow">{tx('ファイル名(.md)', 'File name (.md)')}</span>
			<input
				bind:value={newDataFileName}
				placeholder="note_new.md"
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			/>
		</label>
		<label style="display: grid; gap: 6px; margin-top: 10px;">
			<span class="eyebrow">{tx('内容', 'Content')}</span>
			<textarea
				bind:value={newDataContent}
				rows="5"
				placeholder={tx(
					'ここに追加したい知識を書いてください。',
					'Write knowledge content here.'
				)}
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			></textarea>
		</label>
		<div class="actions" style="margin-top: 10px;">
			<button class="btn-primary" disabled={savingData} onclick={addRagData}
				>{savingData
					? tx('追加中...', 'Adding...')
					: tx('追加してindex更新', 'Add and rebuild index')}</button
			>
		</div>
		{#if saveDataMessage}
			<p
				class="muted"
				style={saveDataStatus === 'FAIL' ? 'color: var(--fail);' : 'color: var(--ok);'}
			>
				{saveDataMessage}
			</p>
		{/if}
		{#if saveDataLog}
			<div class="log-box">{saveDataLog}</div>
		{/if}
	</section>

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">Run</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx(
				'モデルを選んで、RAG追加後の結果を見る',
				'Choose model and see results after RAG updates'
			)}
		</h2>
		<div class="actions" style="margin-top: 10px;">
			<button class="btn-ghost" disabled={refreshingModels} onclick={refreshModelList}
				>{refreshingModels
					? tx('更新中...', 'Refreshing...')
					: tx('モデル一覧を更新', 'Refresh models')}</button
			>
		</div>
		<label style="display: grid; gap: 6px; margin-top: 10px;">
			<span class="eyebrow">{tx('ローカルモデル', 'Local model')}</span>
			<select
				bind:value={selectedModel}
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			>
				{#if modelCatalog.models.length > 0}
					{#each modelCatalog.models as modelName}
						<option value={modelName}>{modelName}</option>
					{/each}
				{:else}
					<option value={selectedModel}>{selectedModel}</option>
				{/if}
			</select>
		</label>
		{#if modelCatalog.error}
			<p class="muted" style="color: var(--warn);">{modelCatalog.error}</p>
		{/if}
		<label style="display: grid; gap: 6px; margin-top: 10px;">
			<span class="eyebrow">{tx('質問', 'Question')}</span>
			<textarea
				bind:value={question}
				rows="3"
				style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
			></textarea>
		</label>
		<div class="actions" style="margin-top: 10px;">
			<button class="btn-primary" disabled={running} onclick={() => askLocalModel()}
				>{running
					? tx('実行中...', 'Running...')
					: tx('ローカルモデルに質問', 'Ask Local Model')}</button
			>
		</div>
		<div class="snippet" style="margin-top: 10px;">{modelRuntimeSummary()}</div>
		<p class="eyebrow" style="margin-top: 10px;">
			{tx('RAG影響サマリー', 'RAG Impact Summary')}
		</p>
		<div class="snippet" style="margin-top: 10px;">{ragImpactSummaryText()}</div>
	</section>
{/if}

{#if !simpleView}
	<section class="hero" style="margin-bottom: 14px;">
		<div class="panel panel-strong">
			<p class="eyebrow">RAG Lab</p>
			<h1 class="title">{tx('現在のRAGと調整ループ', 'Current RAG and Tuning Loop')}</h1>
			<p class="muted">
				{tx(
					'RAG tuning の baseline/candidate 比較と、ローカルモデル応答を同じ画面で検証できます。',
					'Validate baseline/candidate RAG tuning and local model responses on a single screen.'
				)}
			</p>
		</div>
		{#if rag}
			<div class="panel">
				<p class="eyebrow">{tx('現在のスナップショット', 'Current Snapshot')}</p>
				<h2 class="title" style="font-size: 1.2rem;">{rag.title}</h2>
				<div class="pipeline-head" style="margin-top: 10px;">
					<span class={statusClass(rag.status)}>{rag.status}</span>
				</div>
				{#each rag.metrics as metric}
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
		<p class="eyebrow">Learning Path</p>
		<h2 class="title" style="font-size: 1.25rem;">
			{tx('2択チュートリアル', 'Two-Choice Tutorial')}
		</h2>
		<p class="muted">
			{tx(
				'最初に「ガイド」か「上級」を選択できます。トグルでいつでも切替可能です。',
				'Choose Guided or Expert at the start. You can switch anytime with the toggle.'
			)}
		</p>
		<div class="actions" style="margin-top: 10px;">
			<button
				class={mode === 'guided' ? 'btn-primary' : 'btn-ghost'}
				disabled={running}
				onclick={() => selectMode('guided')}>{tx('ガイドで学ぶ', 'Guided mode')}</button
			>
			<button
				class={mode === 'expert' ? 'btn-primary' : 'btn-ghost'}
				disabled={running}
				onclick={() => selectMode('expert')}
				>{tx('わかる人向け調整', 'Expert tuning')}</button
			>
		</div>
		<label class="mode-toggle">
			<input type="checkbox" bind:checked={skipTutorial} />
			<span>
				{tx(
					'チュートリアルを飛ばして上級モードへ',
					'Skip tutorial and switch to expert mode'
				)}
			</span>
		</label>
		{#if mode === 'guided'}
			<div class="phase-grid">
				{#each tutorialPhases as phase}
					<button
						class={`phase-card ${selectedPhase === phase.id ? 'phase-card-active' : ''}`}
						type="button"
						onclick={() => (selectedPhase = phase.id)}
					>
						<div class="pipeline-head">
							<span class="phase-id">Phase {phase.id}</span>
							<span class={statusClass(phaseStatus(phase.id))}
								>{phaseStatus(phase.id)}</span
							>
						</div>
						<p class="phase-title">{phaseTitle(phase)}</p>
						<p class="phase-goal">{phaseGoal(phase)}</p>
					</button>
				{/each}
			</div>
			<div class="actions" style="margin-top: 10px;">
				<button class="btn-primary" disabled={running} onclick={runSelectedPhase}
					>{phaseActionLabel(selectedPhase)}</button
				>
				<button class="btn-ghost" type="button" onclick={advancePhase}
					>{tx('次のフェーズへ', 'Next phase')}</button
				>
			</div>
		{/if}
	</section>

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">Outcome</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('最終的にどうなったか', 'Final Outcome at a Glance')}
		</h2>
		<div class="snippet" style="margin-top: 10px;">{finalOutcomeSummary()}</div>
	</section>

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">RAG Data (Read-only)</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('RAGデータ実体（READ ONLY）', 'RAG Data Reality (READ ONLY)')}
		</h2>
		<p class="muted">
			{tx(
				'data/raw と index の実体を表示します。編集はこの画面から行いません。',
				'Shows actual data/raw and index content. Editing is not available on this screen.'
			)}
		</p>
		<div class="actions" style="margin-top: 10px;">
			<button
				class="btn-ghost"
				disabled={refreshingSnapshot}
				onclick={refreshReadonlySnapshot}
				>{refreshingSnapshot
					? tx('更新中...', 'Refreshing...')
					: tx('READ ONLYデータを更新', 'Refresh read-only data')}</button
			>
		</div>
		{#if snapshot}
			<div class="snippet" style="margin-top: 10px;">{snapshotSummaryText(snapshot)}</div>
			<div class="table-wrap">
				<table class="data-table">
					<thead>
						<tr>
							<th>{tx('ファイル', 'File')}</th>
							<th>{tx('サイズ', 'Size')}</th>
							<th>{tx('更新', 'Updated')}</th>
							<th>{tx('プレビュー', 'Preview')}</th>
						</tr>
					</thead>
					<tbody>
						{#if snapshot.files.length === 0}
							<tr>
								<td colspan="4"
									>{tx(
										'表示できるファイルがありません。',
										'No files available.'
									)}</td
								>
							</tr>
						{:else}
							{#each snapshot.files as file}
								<tr>
									<td class="path">{file.path}</td>
									<td>{formatBytes(file.sizeBytes)}</td>
									<td>{formatLocaleDate(file.modifiedAt)}</td>
									<td class="readonly-preview">{file.preview}</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	{#if mode === 'guided'}
		<section class="panel" style="margin-bottom: 14px;">
			<p class="eyebrow">First Run</p>
			<h2 class="title" style="font-size: 1.3rem;">
				{tx('はじめて使う導線', 'First-run Checklist')}
			</h2>
			<p class="muted">
				{tx(
					'LLM起動 / data / index を順番に確認して、次に押すボタンを案内します。',
					'Check LLM startup, data, and index in sequence, then follow the suggested next button.'
				)}
			</p>
			<div class="actions" style="margin-top: 12px;">
				<div class="action-with-tip">
					<button
						class="btn-ghost"
						disabled={running || checkingGuide}
						onclick={refreshGuide}
						>{checkingGuide
							? tx('確認中...', 'Checking...')
							: tx('状態を再チェック', 'Recheck Status')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('check-status')}
						aria-label={tx('状態を再チェックの説明', 'About Recheck Status')}>i</button
					>
				</div>
				{#if guide}
					<span class={guideReadyClass(guide.readyToAsk)}
						>{guide.readyToAsk
							? tx('質問準備OK', 'Ready to ask')
							: tx('未完了ステップあり', 'Steps remaining')}</span
					>
				{/if}
			</div>
			{#if isTipOpen(['check-status'])}
				<div class="tip-panel" style="margin-top: 10px;">
					<h3>{tipTitle(activeTipId)}</h3>
					<div class="snippet" style="margin-top: 8px;">{tipBody(activeTipId)}</div>
				</div>
			{/if}
			{#if guide}
				<div class="prompt-list" style="margin-top: 12px;">
					{#each guide.checks as check, i}
						<article class="prompt-item" style="padding: 12px 14px;">
							<div class="pipeline-head">
								<h3 class="pipeline-title" style="font-size: 0.98rem;">
									{tx(`STEP ${i + 1}`, `STEP ${i + 1}`)}: {guideTitle(check.id)}
								</h3>
								<span class={statusClass(check.status)}>{check.status}</span>
							</div>
							<p class="muted" style="margin-top: 6px;">
								{guideDetailText(check, guide)}
							</p>
							<p class="muted" style="margin-top: 6px;">
								{tx('次の一手', 'Next')}: {guideNextActionText(check, guide)}
							</p>
							<details class="guide-tech">
								<summary>{tx('技術詳細を表示', 'Show technical details')}</summary>
								<div class="snippet" style="margin-top: 8px;">
									{guideRawText(check)}
								</div>
							</details>
						</article>
					{/each}
				</div>
				{#if firstBlockingCheck()}
					<div class="actions" style="margin-top: 10px;">
						{#if firstBlockingCheck()?.id === 'llm'}
							<div class="action-with-tip">
								<button
									class="btn-primary"
									disabled={running || checkingGuide}
									onclick={refreshGuide}
									>{tx(
										'次に押す: STEP1を再チェック',
										'Next: Recheck STEP1'
									)}</button
								>
								<button
									class="tip-icon-btn"
									type="button"
									onclick={() => toggleTip('check-status')}
									aria-label={tx('STEP1再チェックの説明', 'About STEP1 recheck')}
									>i</button
								>
							</div>
						{:else if firstBlockingCheck()?.id === 'data'}
							<div class="action-with-tip">
								<button
									class="btn-primary"
									disabled={running}
									onclick={() => applyPreset(questionPresets[0])}
									>{tx(
										'次に押す: サンプル質問を入れる',
										'Next: Insert sample question'
									)}</button
								>
								<button
									class="tip-icon-btn"
									type="button"
									onclick={() => toggleTip(`preset:${questionPresets[0].id}`)}
									aria-label={tx(
										'サンプル質問を入れるの説明',
										'About inserting sample question'
									)}>i</button
								>
							</div>
						{:else}
							<div class="action-with-tip">
								<button
									class="btn-primary"
									disabled={running || checkingGuide}
									onclick={refreshGuide}
									>{tx(
										'次に押す: STEP3を再チェック',
										'Next: Recheck STEP3'
									)}</button
								>
								<button
									class="tip-icon-btn"
									type="button"
									onclick={() => toggleTip('check-status')}
									aria-label={tx('STEP3再チェックの説明', 'About STEP3 recheck')}
									>i</button
								>
							</div>
						{/if}
					</div>
				{:else}
					<div class="actions" style="margin-top: 10px;">
						<div class="action-with-tip">
							<button
								class="btn-primary"
								disabled={running}
								onclick={() => runPreset(questionPresets[0])}
								>{tx(
									'次に押す: サンプル質問を実行',
									'Next: Run sample question'
								)}</button
							>
							<button
								class="tip-icon-btn"
								type="button"
								onclick={() => toggleTip('run-sample')}
								aria-label={tx('サンプル質問実行の説明', 'About sample run')}
								>i</button
							>
						</div>
					</div>
				{/if}
				<div class="snippet" style="margin-top: 10px;">{guideSummaryText(guide)}</div>
			{/if}
		</section>

		<section class="panel" style="margin-bottom: 14px;">
			<p class="eyebrow">Tutorial</p>
			<h2 class="title" style="font-size: 1.25rem;">
				{tx('RAGを理解して使う（初学者向け）', 'Understand RAG (Beginner Guide)')}
			</h2>
			<p class="muted">
				{tx(
					'この画面のボタンを押したときに、内部で何が起きるかを順番に説明します。',
					'This explains what happens internally when each button on this page is pressed.'
				)}
			</p>
			<div class="prompt-list" style="margin-top: 10px;">
				<details class="prompt-item" open>
					<summary
						>{tx('1. RAGとは？なぜ必要？', '1. What is RAG and why use it?')}</summary
					>
					<div class="prompt-body">
						<p class="muted">
							{tx(
								'RAGは、質問時にローカル資料（data/raw）から根拠候補を検索し、その根拠だけを使って回答する方式です。これにより「それっぽい推測」を減らし、参照付きで監査しやすくなります。',
								'RAG retrieves evidence candidates from local docs (data/raw) and answers using only that evidence. This reduces speculation and makes answers auditable with references.'
							)}
						</p>
					</div>
				</details>
				<details class="prompt-item">
					<summary
						>{tx(
							'2. ボタンを押すと内部で何が起きる？',
							'2. What happens when you click each button?'
						)}</summary
					>
					<div class="prompt-body">
						<div class="snippet">
							{tx(
								'状態を再チェック: LLM API(/models), data/raw, index DB を確認\n1クリック: サンプル質問を実行: src/ask.py が index を検索し、CONTEXTを作成してLLMに送信\nローカルモデルに質問: 入力した質問で同じ処理を実行\nRAG調整ループを実行: tuningスクリプトを実行し、指標/evidenceを更新',
								'Recheck Status: verify LLM API(/models), data/raw, and index DB\nOne-click sample run: src/ask.py searches index, builds CONTEXT, then calls LLM\nAsk Local Model: same flow with your custom question\nRun RAG Tuning Loop: execute tuning script and refresh metrics/evidence'
							)}
						</div>
					</div>
				</details>
				<details class="prompt-item">
					<summary
						>{tx(
							'3. 「不明 / CONTEXTが空」が出る理由',
							'3. Why "unknown / CONTEXT empty" appears'
						)}</summary
					>
					<div class="prompt-body">
						<p class="muted">
							{tx(
								'クラッシュではなく、根拠検索でヒットが少ない状態です。質問文を具体化（ファイル名・キーワード明示）するか、data/raw と index の内容を増やすと改善します。',
								'It is not a crash; retrieval had too few matches. Make the question more concrete (file name/keywords), or improve data/raw and index content.'
							)}
						</p>
					</div>
				</details>
				<details class="prompt-item">
					<summary
						>{tx(
							'4. RAGを作りすぎると何が悪い？',
							'4. What goes wrong when RAG is overdone?'
						)}</summary
					>
					<div class="prompt-body">
						<div class="snippet">
							{tx(
								'参照過多(top_k過大): 回答が散らかり、遅くなる\nchunk大きすぎ: ノイズ混入で精度低下\nchunk小さすぎ: 文脈分断で根拠不足\n対策: まず少数データ + 小さなtop_kで始め、1変更ごとに hit_rate/latency を見る',
								'Too many references (high top_k): noisy and slower answers\nChunks too large: precision drops due to noise\nChunks too small: context fragmentation\nApproach: start with small data and low top_k, then track hit_rate/latency per change'
							)}
						</div>
					</div>
				</details>
			</div>
		</section>

		<section class="panel" style="margin-bottom: 14px;">
			<p class="eyebrow">Workshop</p>
			<h2 class="title" style="font-size: 1.25rem;">
				{tx('3ステップ実践ワークショップ', 'Hands-on Workshop in 3 Steps')}
			</h2>
			<p class="muted">
				{tx(
					'各ステップに「何が起きるか」「成功サイン」を固定表示しています。iボタンを開かなくても進められます。',
					'Each step shows internal flow and success signals by default, so you can proceed without opening tip popups.'
				)}
			</p>
			<div class="workshop-grid">
				<article class="workshop-card">
					<p class="eyebrow">STEP 1</p>
					<h3 class="pipeline-title">{tx('まず動かす', 'Run first')}</h3>
					<p class="muted">
						{tx(
							'hello.md のサンプル質問を実行し、RAGの基本フローが通るか確認します。',
							'Run the hello.md sample and verify the baseline RAG flow.'
						)}
					</p>
					<div class="snippet">
						{tx(
							'内部で実行:\n- POST /api/dashboard/ai-lab/run\n- channel=local-model\n- src/ask.py (index検索→CONTEXT生成→LLM呼び出し)',
							'Internal flow:\n- POST /api/dashboard/ai-lab/run\n- channel=local-model\n- src/ask.py (index search -> context build -> LLM call)'
						)}
					</div>
					<div class="actions" style="margin-top: 10px;">
						<button
							class="btn-primary"
							disabled={running}
							onclick={() => runPreset(questionPresets[0])}
							>{tx('STEP1を実行', 'Run STEP1')}</button
						>
					</div>
					<p class="workshop-result">
						{tx(
							'成功サイン: 最新出力に結論/根拠/参照が埋まり、Execution Trace が PASS になる。',
							'Success signal: Latest Output contains conclusion/evidence/reference and Execution Trace is PASS.'
						)}
					</p>
				</article>

				<article class="workshop-card">
					<p class="eyebrow">STEP 2</p>
					<h3 class="pipeline-title">
						{tx('質問を変えて比較する', 'Compare with another question')}
					</h3>
					<p class="muted">
						{tx(
							'別テンプレ質問で再実行し、参照先や回答品質の違いを観察します。',
							'Run another template question and observe reference/quality differences.'
						)}
					</p>
					<div class="snippet">
						{tx(
							'注目ポイント:\n- 参照が質問に合っているか\n- 「不明」になったときは data/index と質問具体度を見直す',
							'Focus points:\n- Whether references match your question\n- If output becomes "unknown", review data/index and question specificity'
						)}
					</div>
					<div class="actions" style="margin-top: 10px;">
						<button
							class="btn-ghost"
							disabled={running}
							onclick={() => applyPreset(questionPresets[1])}
							>{tx('テンプレを入れる', 'Insert template')}</button
						>
						<button
							class="btn-primary"
							disabled={running}
							onclick={() => runPreset(questionPresets[1])}
							>{tx('STEP2を実行', 'Run STEP2')}</button
						>
					</div>
					<p class="workshop-result">
						{tx(
							'成功サイン: STEP1と比べて、参照ファイルや回答内容の差分を説明できる。',
							'Success signal: You can explain differences from STEP1 in references and answer content.'
						)}
					</p>
				</article>

				<article class="workshop-card">
					<p class="eyebrow">STEP 3</p>
					<h3 class="pipeline-title">{tx('調整して評価する', 'Tune and evaluate')}</h3>
					<p class="muted">
						{tx(
							'RAG調整ループを回し、ヒット率と遅延の差分を確認します。',
							'Run the tuning loop and inspect hit-rate and latency deltas.'
						)}
					</p>
					<div class="snippet">
						{tx(
							'内部で実行:\n- POST /api/dashboard/ai-lab/run (rag-tuning)\n- scripts/ops/s25_rag_tuning_loop.py\n- その後に指標再取得',
							'Internal flow:\n- POST /api/dashboard/ai-lab/run (rag-tuning)\n- scripts/ops/s25_rag_tuning_loop.py\n- Then refresh metrics'
						)}
					</div>
					<div class="actions" style="margin-top: 10px;">
						<button class="btn-primary" disabled={running} onclick={runRagTuning}
							>{tx('STEP3を実行', 'Run STEP3')}</button
						>
						<button class="btn-ghost" disabled={running} onclick={refreshOverview}
							>{tx('指標を再取得', 'Reload metrics')}</button
						>
					</div>
					<p class="workshop-result">
						{tx(
							'成功サイン: Snapshot の値が更新され、改善/悪化を言語化できる。',
							'Success signal: Snapshot values update and you can describe improvements or regressions.'
						)}
					</p>
				</article>
			</div>
		</section>
	{/if}

	{#if mode === 'expert'}
		<section class="panel" style="margin-bottom: 14px;">
			<p class="eyebrow">Actions</p>
			<h2 class="title" style="font-size: 1.3rem;">{tx('詳細操作', 'Advanced Controls')}</h2>
			<p class="muted">
				{tx(
					'上のWorkshopを終えたあとに、個別操作や再実行を行うための操作群です。',
					'Use these controls for fine-grained operations after completing the Workshop.'
				)}
			</p>
			<div class="actions" style="margin-top: 12px;">
				<div class="action-with-tip">
					<button class="btn-primary" disabled={running} onclick={runRagTuning}
						>{running
							? tx('実行中...', 'Running...')
							: tx('RAG調整ループを実行', 'Run RAG Tuning Loop')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('run-rag-tuning')}
						aria-label={tx('RAG調整ループを実行の説明', 'About run rag tuning loop')}
						>i</button
					>
				</div>
				<div class="action-with-tip">
					<button class="btn-ghost" disabled={running} onclick={refreshOverview}
						>{tx('指標を更新', 'Refresh Metrics')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('refresh-metrics')}
						aria-label={tx('指標更新の説明', 'About refresh metrics')}>i</button
					>
				</div>
			</div>
			<label style="display: grid; gap: 6px; margin-top: 12px;">
				<span class="eyebrow">{tx('ローカルモデルへの質問', 'Local model question')}</span>
				<textarea
					bind:value={question}
					rows="3"
					style="padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); font: inherit;"
				></textarea>
			</label>
			<div class="actions" style="margin-top: 10px;">
				{#each questionPresets as preset}
					<div class="action-with-tip">
						<button
							class="btn-ghost"
							disabled={running}
							onclick={() => applyPreset(preset)}>{presetLabel(preset)}</button
						>
						<button
							class="tip-icon-btn"
							type="button"
							onclick={() => toggleTip(`preset:${preset.id}`)}
							aria-label={tx('質問テンプレートの説明', 'About question template')}
							>i</button
						>
					</div>
				{/each}
			</div>
			<div class="actions" style="margin-top: 10px;">
				<div class="action-with-tip">
					<button
						class="btn-primary"
						disabled={running}
						onclick={() => runPreset(questionPresets[0])}
						>{tx(
							'1クリック: サンプル質問を実行',
							'One-click: Run sample question'
						)}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('run-sample')}
						aria-label={tx('1クリック実行の説明', 'About one-click sample run')}
						>i</button
					>
				</div>
				<div class="action-with-tip">
					<button class="btn-ghost" disabled={running} onclick={() => askLocalModel()}
						>{tx('ローカルモデルに質問', 'Ask Local Model')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('ask-local')}
						aria-label={tx('ローカルモデルに質問の説明', 'About ask local model')}
						>i</button
					>
				</div>
			</div>
			{#if isTipOpen( ['run-rag-tuning', 'refresh-metrics', 'ask-local', 'run-sample'] ) || activeTipId.startsWith('preset:')}
				<div class="tip-panel" style="margin-top: 10px;">
					<h3>{tipTitle(activeTipId)}</h3>
					<div class="snippet" style="margin-top: 8px;">{tipBody(activeTipId)}</div>
				</div>
			{/if}
			{#if error}
				<p class="muted" style="color: var(--fail);">{error}</p>
			{/if}
		</section>
	{/if}

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">Coach</p>
		<h2 class="title" style="font-size: 1.2rem;">
			{tx('結果の読み解き', 'How to read your result')}
		</h2>
		<p class="muted">{coachTitle()}</p>
		<p class="muted">{coachNarrative()}</p>
		<div class="snippet" style="margin-top: 10px;">{coachNextMoves()}</div>
	</section>

	{#if lastAction}
		<section class="panel" style="margin-bottom: 14px;">
			<p class="eyebrow">Execution Trace</p>
			<h2 class="title" style="font-size: 1.2rem;">
				{tx('直前に何を実行したか', 'What just executed')}
			</h2>
			<div class="metric-row">
				<span class="metric-label">{tx('ステータス', 'Status')}</span>
				<span class={statusClass(lastAction.status)}>{lastAction.status}</span>
			</div>
			<div class="metric-row">
				<span class="metric-label">{tx('実行時刻', 'Requested at')}</span>
				<span class="metric-value"
					>{new Date(lastAction.requestedAt).toLocaleString(
						localeState.value === 'ja' ? 'ja-JP' : 'en-US'
					)}</span
				>
			</div>
			<div class="snippet" style="margin-top: 10px;">{traceSummary(lastAction)}</div>
		</section>
	{/if}

	{#if latestLog && isContextEmpty(latestLog)}
		<section class="panel" style="margin-bottom: 14px;">
			<p class="eyebrow">Empty Context Help</p>
			<h2 class="title" style="font-size: 1.2rem;">
				{tx('CONTEXTが空のときの次アクション', 'Next Actions when CONTEXT is empty')}
			</h2>
			<p class="muted">
				{tx(
					'失敗ではなく「根拠が見つからない」状態です。まずサンプル質問で動作確認し、次に data/raw と index を再チェックしてください。',
					'This is not a crash; it means no evidence was found. Run a sample question first, then recheck data/raw and index.'
				)}
			</p>
			<div class="actions" style="margin-top: 10px;">
				<div class="action-with-tip">
					<button
						class="btn-primary"
						disabled={running}
						onclick={() => runPreset(questionPresets[0])}
						>{tx('サンプル質問を実行', 'Run sample question')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('run-sample')}
						aria-label={tx('サンプル質問実行の説明', 'About sample run')}>i</button
					>
				</div>
				<div class="action-with-tip">
					<button
						class="btn-ghost"
						disabled={running}
						onclick={() => runPreset(questionPresets[1])}
						>{tx('sample_note質問を実行', 'Run sample_note question')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip(`preset:${questionPresets[1].id}`)}
						aria-label={tx('sample_note質問の説明', 'About sample_note question')}
						>i</button
					>
				</div>
				<div class="action-with-tip">
					<button
						class="btn-ghost"
						disabled={running || checkingGuide}
						onclick={refreshGuide}
						>{tx('環境を再チェック', 'Recheck environment')}</button
					>
					<button
						class="tip-icon-btn"
						type="button"
						onclick={() => toggleTip('check-status')}
						aria-label={tx('環境再チェックの説明', 'About environment recheck')}
						>i</button
					>
				</div>
			</div>
			{#if isTipOpen( ['run-sample', 'check-status'] ) || activeTipId === `preset:${questionPresets[1].id}`}
				<div class="tip-panel" style="margin-top: 10px;">
					<h3>{tipTitle(activeTipId)}</h3>
					<div class="snippet" style="margin-top: 8px;">{tipBody(activeTipId)}</div>
				</div>
			{/if}
			{#if guide}
				<div class="snippet" style="margin-top: 10px;">
					{emptyContextSummaryText(guide)}
				</div>
			{/if}
		</section>
	{/if}

	<section class="panel" style="margin-bottom: 14px;">
		<p class="eyebrow">SOT Preview</p>
		<h2 class="title" style="font-size: 1.2rem;">S25-08_RAG_TUNING.toml</h2>
		<div class="snippet">{data.ragConfigPreview}</div>
	</section>
{/if}

{#if latestLog}
	<section class="panel">
		<p class="eyebrow">{tx('最新出力', 'Latest Output')}</p>
		<h2 class="title" style="font-size: 1.1rem;">{latestStatus || tx('結果', 'result')}</h2>
		<div class="log-box">{latestLog}</div>
	</section>
{/if}
