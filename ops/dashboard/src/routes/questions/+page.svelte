<script lang="ts">
	import { getContext } from 'svelte';

	import {
		classifyChatRunFailure,
		presentQuestionRun,
		type PresentedQuestionRun,
		type QuestionEvidenceItem,
		type QuestionNoticeCode,
		type QuestionsFailureKind
	} from '$lib/questions/presenter';
	import {
		buildQuestionGuidance,
		deriveQuestionExamples,
		deriveQuestionScopeChips,
		type QuestionSuggestion
	} from '$lib/questions/asking';
	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';
	import type { ChatRunResponse, RagSourceItem } from '$lib/server/types';

	interface PageData {
		sources: RagSourceItem[];
		sourcesDegraded: boolean;
		sourcesMessageJa: string | null;
		sourcesMessageEn: string | null;
	}

	type QuestionUiState =
		| 'idle'
		| 'blank'
		| 'no_documents'
		| 'answer'
		| 'unknown'
		| QuestionsFailureKind;

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);
	let { data }: { data: PageData } = $props();

	let question = $state('');
	let submitting = $state(false);
	let uiState = $state<QuestionUiState>('idle');
	let result = $state<PresentedQuestionRun | null>(null);
	let lastQuestion = $state('');
	let selectedScopeId = $state<string | null>(null);

	const enabledSources = $derived(data.sources.filter((item) => item.enabled));
	const enabledSourceIds = $derived(enabledSources.map((item) => item.id));
	const selectedScope = $derived(enabledSources.find((item) => item.id === selectedScopeId) ?? null);
	const effectiveSourceIds = $derived(selectedScope ? [selectedScope.id] : enabledSourceIds);
	const scopeChips = $derived(deriveQuestionScopeChips(enabledSources, localeState.value));
	const exampleQuestions = $derived(
		deriveQuestionExamples(enabledSources, localeState.value, selectedScope?.id ?? null)
	);
	const questionGuidance = $derived(
		buildQuestionGuidance({
			locale: localeState.value,
			question: submitting ? lastQuestion : question,
			sources: enabledSources,
			selectedScopeId: selectedScope?.id ?? null,
			uiState,
			result
		})
	);
	const latestUpdatedAt = $derived(data.sources[0]?.updatedAt ?? null);

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	function dt(isoLike: string | null): string {
		if (!isoLike) {
			return tx('未登録', 'Not available');
		}
		return new Date(isoLike).toLocaleString(localeState.value === 'ja' ? 'ja-JP' : 'en-US');
	}

	function stateBannerClass(): string {
		if (submitting) {
			return 'status-banner status-banner-info';
		}
		if (uiState === 'answer') {
			return 'status-banner status-banner-ok';
		}
		if (uiState === 'backend_unavailable' || uiState === 'server_failure') {
			return 'status-banner status-banner-fail';
		}
		if (uiState === 'blank' || uiState === 'no_documents' || uiState === 'unknown') {
			return 'status-banner status-banner-warn';
		}
		return 'status-banner status-banner-info';
	}

	function stateBannerText(): string {
		if (submitting) {
			return tx(
				'質問を送信しています。答えと根拠候補をこの画面でまとめます。',
				'Sending the question. The answer and supporting document candidates will appear on this screen.'
			);
		}
		switch (uiState) {
			case 'blank':
				return tx(
					'質問文が空です。まず 1 つだけ自然言語で入れてください。',
					'The question is empty. Enter one natural-language question first.'
				);
			case 'no_documents':
				return tx(
					'今は使える資料がありません。まず Documents で一覧を確認してください。',
					'No usable documents are available yet. Check Documents first.'
				);
			case 'answer':
				return tx(
					'答えと関連資料を同じ画面にまとめました。',
					'The answer and related documents are summarized on the same screen.'
				);
			case 'unknown':
				return (
					questionGuidance.diagnosis ||
					tx(
						'不明は失敗ではありません。今の資料で足りない点を下に示します。',
						'Unknown is not a failure. The missing support in the current documents is shown below.'
					)
				);
			case 'backend_unavailable':
				return tx(
					'モデルまたはバックエンドに接続できません。',
					'The model or backend is not reachable right now.'
				);
			case 'server_failure':
				return tx(
					'サーバー処理に失敗しました。時間をおいて再実行してください。',
					'The server failed to process the request. Try again in a moment.'
				);
			default:
				return tx(
					'資料に入っていそうなことを 1 つだけ質問してください。',
					'Ask one thing that should be answerable from the loaded documents.'
				);
		}
	}

	function answerText(): string {
		if (uiState === 'answer') {
			return (
				result?.answer ||
				tx('答えをまとめました。', 'The answer has been summarized.')
			);
		}
		if (uiState === 'unknown') {
			return (
				result?.answer ||
				tx(
					'現在の資料だけでは、この質問に答え切る根拠を確認できません。',
					'The current documents do not provide enough support to answer this question yet.'
				)
			);
		}
		if (uiState === 'blank') {
			return tx(
				'質問を入力すると、ここに短い答えが表示されます。',
				'Enter a question to see a short answer here.'
			);
		}
		if (uiState === 'no_documents') {
			return tx(
				'資料が 0 件のため、まだ答えを作れません。',
				'There are no documents yet, so an answer cannot be produced.'
			);
		}
		if (uiState === 'backend_unavailable') {
			return tx(
				'今はモデルに接続できないため、回答を返せません。',
				'The system cannot reach the model right now, so it cannot return an answer.'
			);
		}
		if (uiState === 'server_failure') {
			return tx(
				'今は処理に失敗しているため、回答を返せません。',
				'The request failed during processing, so no answer can be returned right now.'
			);
		}
		return tx(
			'質問を送ると、この場所に最初の答えが短く表示されます。',
			'Send a question and the first concise answer will appear here.'
		);
	}

	function evidenceReasonText(item: QuestionEvidenceItem): string {
		if (item.matches.length === 0) {
			return tx(
				'今回の質問に関連すると判断された資料候補です。',
				'This document was treated as relevant to the current question.'
			);
		}
		const lines = item.matches.map((match) => {
			switch (match.kind) {
				case 'selected':
					return tx(
						'現在の知識ベースに含まれている資料です。',
						'This document is currently included in the knowledge base.'
					);
				case 'name':
					return tx(
						`資料名に「${match.term ?? ''}」が含まれます。`,
						`Its title includes "${match.term ?? ''}".`
					);
				case 'tag':
					return tx(
						`タグに「${match.term ?? ''}」が含まれます。`,
						`Its tags include "${match.term ?? ''}".`
					);
				case 'path':
					return tx(
						`保存先に「${match.term ?? ''}」が含まれます。`,
						`Its path includes "${match.term ?? ''}".`
					);
				case 'description':
					return tx(
						`説明文に「${match.term ?? ''}」が含まれます。`,
						`Its description includes "${match.term ?? ''}".`
					);
				default:
					return tx(
						'質問に関連する資料候補として参照されました。',
						'It was referenced as a candidate related to the question.'
					);
			}
		});
		return lines.slice(0, 2).join(' ');
	}

	function evidenceEmptyText(): string {
		if (uiState === 'idle' || uiState === 'blank') {
			return tx(
				'質問を送ると、ここに関連資料の候補が並びます。',
				'Send a question to see the related document candidates here.'
			);
		}
		if (uiState === 'no_documents') {
			return tx(
				'まだ参照できる資料がありません。',
				'There are no documents available to cite yet.'
			);
		}
		if (uiState === 'backend_unavailable' || uiState === 'server_failure') {
			return tx(
				'資料候補を整形する前に処理が止まりました。',
				'The request stopped before supporting documents could be prepared.'
			);
		}
		return tx(
			'今回の質問に合う資料候補が見つかっていません。',
			'No document candidates matched this question.'
		);
	}

	function documentsEmptyText(): string {
		if (uiState === 'no_documents') {
			return tx(
				'まず Documents で登録済み資料を確認してください。',
				'Check the registered documents in Documents first.'
			);
		}
		if (uiState === 'backend_unavailable' || uiState === 'server_failure') {
			return tx(
				'今回は資料一覧まで整理できませんでした。',
				'The request did not reach the point where the used documents could be listed.'
			);
		}
		return tx(
			'今回の質問で使われた資料はまだありません。',
			'No documents were used for this question yet.'
		);
	}

	function noticeText(code: QuestionNoticeCode): string {
		switch (code) {
			case 'candidate_evidence_only':
				return tx(
					'今の根拠表示は「関連資料候補」です。必要なら Evidence で元資料を見直してください。',
					'The current evidence view shows related document candidates. Use Evidence to inspect the originals when needed.'
				);
			case 'no_matching_documents':
				return tx(
					'この質問に合う資料が、今の知識ベースから見つかっていません。',
					'The current knowledge base does not yet contain a matching document for this question.'
				);
			case 'clarify_question':
				return tx(
					'文書名、期間、対象機能を入れて質問を絞ると次は答えやすくなります。',
					'Add a document name, timeframe, or target feature to narrow the next question.'
				);
			case 'verify_before_reuse':
				return tx(
					'この答えをそのまま使う前に、Evidence で元資料を確認してください。',
					'Before reusing this answer, verify the original documents in Evidence.'
				);
		}
	}

	function noteItems(): string[] {
		const items: string[] = [];

		if (uiState === 'blank') {
			items.push(
				tx(
					'まず 1 つだけ質問を入力してください。',
					'Enter one question first.'
				)
			);
		}
		if (uiState === 'no_documents') {
			items.push(
				tx(
					'資料がまだ 0 件です。Documents で一覧を確認し、必要な資料をそろえてから再実行してください。',
					'There are still zero documents. Review Documents and gather the needed material before trying again.'
				)
			);
		}
		if (uiState === 'backend_unavailable') {
			items.push(
				tx(
					'ローカルモデルかバックエンドの起動状態を確認してから再実行してください。',
					'Check whether the local model or backend is running, then try again.'
				)
			);
		}
		if (uiState === 'server_failure') {
			items.push(
				tx(
					'一時的な失敗の可能性があります。少し待ってから再実行してください。',
					'This may be a temporary failure. Wait briefly and try again.'
				)
			);
		}
		for (const code of result?.notices || []) {
			items.push(noticeText(code));
		}
		if (data.sourcesDegraded && (data.sourcesMessageJa || data.sourcesMessageEn)) {
			items.push(tx(data.sourcesMessageJa ?? '', data.sourcesMessageEn ?? ''));
		}
		return Array.from(new Set(items.filter(Boolean)));
	}

	function setScope(sourceId: string | null) {
		selectedScopeId = sourceId;
	}

	function applySuggestion(item: QuestionSuggestion) {
		question = item.text;
		selectedScopeId = item.sourceId;
	}

	function showResultBlocks(): boolean {
		return submitting || uiState !== 'idle';
	}

	async function submitQuestion(event: SubmitEvent) {
		event.preventDefault();
		const text = question.trim();
		lastQuestion = text;
		result = null;

		if (!text) {
			uiState = 'blank';
			return;
		}
		if (enabledSourceIds.length === 0) {
			uiState = 'no_documents';
			return;
		}

		submitting = true;
		try {
			const res = await fetch('/api/dashboard/chat/run', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					message: text,
					selectedRagIds: effectiveSourceIds
				})
			});
			const payload = (await res.json()) as
				| ChatRunResponse
				| {
						error?: string;
						kind?: QuestionsFailureKind;
				  };
			if (!res.ok) {
				uiState =
					('kind' in payload && payload.kind) ||
					classifyChatRunFailure(('error' in payload && payload.error) || '');
				return;
			}
			result = presentQuestionRun(payload as ChatRunResponse);
			uiState = result.kind;
		} catch {
			uiState = 'server_failure';
		} finally {
			submitting = false;
		}
	}
</script>

<div class="surface-stack">
	<section class="hero">
		<article class="panel panel-strong">
			<p class="eyebrow">{tx('質問', 'Questions')}</p>
			<h1 class="title">
				{tx(
					'普通の言い方で、そのまま質問できる面です。',
					'Ask in ordinary language without adapting to the system.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'資料名を正確に覚えていなくても大丈夫です。今の資料を裏で見に行き、答えと関連資料候補を同じ画面にまとめます。',
					'You do not need exact document names. The system will look through the current documents behind the scenes and keep the answer plus related document candidates on this page.'
				)}
			</p>

			<form class="question-form" onsubmit={submitQuestion}>
				<label class="question-label" for="main-question-input">
					{tx('知りたいこと', 'What do you want to know?')}
				</label>
				<p class="question-helper-copy">
					{tx(
						'まずはいつもの言い方で聞いてください。必要なら下の例や任意の範囲指定で少しだけ絞れます。',
						'Start with your normal wording. If helpful, use the examples or the optional scope chips below to narrow it a little.'
					)}
				</p>
				<textarea
					id="main-question-input"
					class="question-input"
					bind:value={question}
					rows="5"
					placeholder={tx(
						'例: main path は何面に整理されている？',
						'Example: How is the main path organized right now?'
					)}
				></textarea>
				<div class="question-helper-group">
					<p class="question-helper-label">
						{tx('必要なら範囲を絞る', 'Optional scope')}
					</p>
					<p class="question-helper-copy question-helper-copy-compact">
						{tx(
							'指定しなくても質問できます。選ぶと、その資料を優先して裏で見に行きます。',
							'You can ask without choosing one. If you pick one, the system will prefer that document behind the scenes.'
						)}
					</p>
					<div class="chip-row">
						{#each scopeChips as item}
							<button
								type="button"
								class={`chip-btn ${selectedScope?.id === item.sourceId || (!selectedScope && item.sourceId === null) ? 'chip-btn-active' : ''}`}
								aria-pressed={selectedScope?.id === item.sourceId || (!selectedScope && item.sourceId === null)}
								onclick={() => setScope(item.sourceId)}>{item.label}</button
							>
						{/each}
					</div>
				</div>
				{#if exampleQuestions.length > 0}
					<div class="question-helper-group">
						<p class="question-helper-label">
							{tx('今の資料から聞きやすい例', 'Good questions for the current documents')}
						</p>
						<div class="chip-row">
							{#each exampleQuestions as item}
								<button
									type="button"
									class="chip-btn chip-btn-soft"
									onclick={() => applySuggestion(item)}>{item.text}</button
								>
							{/each}
						</div>
					</div>
				{/if}
				<div class="question-toolbar">
					<button type="submit" class="btn-primary" disabled={submitting}>
						{submitting ? tx('送信中...', 'Asking...') : tx('質問する', 'Ask')}
					</button>
					<a class="btn-link btn-ghost" href="/">{tx('資料を見る', 'Open Documents')}</a>
					<a class="btn-link btn-ghost" href="/evidence">{tx('根拠を見る', 'Open Evidence')}</a>
				</div>
			</form>

			<div class={stateBannerClass()} aria-live="polite">
				{stateBannerText()}
			</div>
		</article>

		<article class="panel">
			<p class="eyebrow">{tx('今の資料', 'Current documents')}</p>
			<h2 class="section-title">
				{tx(
					'今の資料でどこまで答えられそうかだけを先に確認できます。',
					'This panel only tells you how ready the current documents are to answer.'
				)}
			</h2>
			<div class="surface-meta">
				<div class="meta-card">
					<p class="meta-label">{tx('登録済み資料', 'Registered documents')}</p>
					<p class="meta-value">{data.sources.length}</p>
				</div>
				<div class="meta-card">
					<p class="meta-label">{tx('有効な資料', 'Enabled documents')}</p>
					<p class="meta-value">{enabledSources.length}</p>
				</div>
				<div class="meta-card">
					<p class="meta-label">{tx('最終更新', 'Last updated')}</p>
					<p class="meta-copy">{dt(latestUpdatedAt)}</p>
				</div>
			</div>
			<ul class="flat-list">
				<li>
					{tx(
						'資料名が曖昧でも大丈夫です。近い資料があれば後で案内します。',
						'Exact document names are not required. If a close current document exists, the page will guide you to it.'
					)}
				</li>
				<li>
					{tx(
						'答えが出なくても失敗ではありません。質問が広すぎるか、根拠がまだ弱い可能性があります。',
						'Not getting an answer is not a failure. The question may still be too broad, or the support may still be too weak.'
					)}
				</li>
				<li>
					{tx(
						'必要なら下の同じ画面で次の質問候補も出します。',
						'When needed, the same screen will suggest a few next questions to try.'
					)}
				</li>
			</ul>
			{#if data.sourcesDegraded && (data.sourcesMessageJa || data.sourcesMessageEn)}
				<p class="section-copy">{tx(data.sourcesMessageJa ?? '', data.sourcesMessageEn ?? '')}</p>
			{/if}
		</article>
	</section>

	<section class="panel" aria-busy={submitting}>
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('結果', 'Result')}</p>
				<h2 class="section-title">
					{tx(
						'返し方は 4 ブロックだけに絞ります。',
						'The response stays limited to four blocks.'
					)}
				</h2>
			</div>
			{#if lastQuestion}
				<p class="section-copy question-memory">
					{tx('直前の質問', 'Latest question')}: {lastQuestion}
				</p>
			{/if}
		</div>

		{#if showResultBlocks()}
			<div class="result-grid">
				<article class="surface-card result-card">
					<p class="eyebrow">{tx('答え', 'Answer')}</p>
					<p class="result-copy">{answerText()}</p>
				</article>

				<article class="surface-card result-card">
					<p class="eyebrow">{tx('根拠', 'Evidence')}</p>
					{#if result?.evidence && result.evidence.length > 0}
						<div class="evidence-list">
							{#each result.evidence as item}
								<div class="evidence-item">
									<p class="result-strong">{item.sourceName}</p>
									<p class="path">{item.sourcePath || tx('パス未設定', 'Path not set')}</p>
									<p class="section-copy">{evidenceReasonText(item)}</p>
									{#if item.preview}
										<p class="snippet">{item.preview}</p>
									{/if}
								</div>
							{/each}
						</div>
					{:else}
						<p class="section-copy">{evidenceEmptyText()}</p>
					{/if}
				</article>

				<article class="surface-card result-card">
					<p class="eyebrow">{tx('使われた資料', 'Documents used')}</p>
					{#if result?.documentsUsed && result.documentsUsed.length > 0}
						<div class="document-list">
							{#each result.documentsUsed as item}
								<div class="document-item">
									<p class="result-strong">{item.name}</p>
									<p class="path">{item.path || tx('パス未設定', 'Path not set')}</p>
								</div>
							{/each}
						</div>
					{:else}
						<p class="section-copy">{documentsEmptyText()}</p>
					{/if}
				</article>

				<article class="surface-card result-card">
					<p class="eyebrow">{tx('分からないこと / 注意点', 'Unknowns / Cautions')}</p>
					{#if questionGuidance.diagnosis}
						<p class="section-copy guidance-diagnosis">{questionGuidance.diagnosis}</p>
					{/if}
					{#if questionGuidance.likelyMatches.length > 0}
						<div class="document-list guidance-match-list">
							<p class="question-helper-label">
								{tx('近い現在資料', 'Likely current documents')}
							</p>
							{#each questionGuidance.likelyMatches as item}
								<div class="document-item">
									<p class="result-strong">{item.name}</p>
									<p class="path">{item.path || tx('パス未設定', 'Path not set')}</p>
								</div>
							{/each}
						</div>
					{/if}
					{#if noteItems().length > 0}
						<ul class="flat-list compact-list">
							{#each noteItems() as item}
								<li>{item}</li>
							{/each}
						</ul>
					{:else if !questionGuidance.diagnosis}
						<p class="section-copy">
							{tx(
								'今のところ追加の注意点はありません。',
								'There are no extra cautions right now.'
							)}
						</p>
					{/if}
					{#if questionGuidance.reaskSuggestions.length > 0}
						<div class="question-helper-group guidance-actions">
							<p class="question-helper-label">
								{tx('次に試す質問', 'Try one of these next')}
							</p>
							<div class="chip-row">
								{#each questionGuidance.reaskSuggestions as item}
									<button
										type="button"
										class="chip-btn chip-btn-soft"
										onclick={() => applySuggestion(item)}>{item.text}</button
									>
								{/each}
							</div>
						</div>
					{/if}
				</article>
			</div>
		{:else}
			<div class="empty-state">
				<p class="section-title">
					{tx(
						'質問すると、答え・根拠・使われた資料・注意点がここに並びます。',
						'Once you ask, the answer, evidence, documents used, and cautions will appear here.'
					)}
				</p>
				<p class="section-copy">
					{tx(
						'まずは、資料に書かれていそうなことを 1 つだけ聞いてください。',
						'Start with one thing that should be contained in the current documents.'
					)}
				</p>
			</div>
		{/if}
	</section>
</div>

<style>
	.question-form {
		display: grid;
		gap: 12px;
		margin-top: 18px;
	}

	.question-label {
		font-family: 'IBM Plex Mono', monospace;
		font-size: 0.76rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--muted);
	}

	.question-helper-label {
		font-family: 'IBM Plex Mono', monospace;
		font-size: 0.72rem;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--muted);
	}

	.question-helper-copy {
		color: var(--muted);
		line-height: 1.55;
	}

	.question-helper-copy-compact {
		margin-top: 4px;
		font-size: 0.9rem;
	}

	.question-input {
		width: 100%;
		min-height: 136px;
		padding: 14px 16px;
		border-radius: 16px;
		border: 1px solid var(--line);
		background: rgba(255, 255, 255, 0.92);
		font: inherit;
		line-height: 1.6;
		resize: vertical;
		color: var(--ink);
	}

	.question-input:focus {
		outline: 2px solid rgba(11, 138, 164, 0.28);
		outline-offset: 2px;
	}

	.question-toolbar {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		align-items: center;
	}

	.question-helper-group {
		display: grid;
		gap: 8px;
	}

	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.chip-btn {
		padding: 9px 12px;
		border-radius: 999px;
		border: 1px solid rgba(11, 138, 164, 0.2);
		background: rgba(255, 255, 255, 0.88);
		color: var(--ink);
		font-weight: 600;
		line-height: 1.35;
		text-align: left;
	}

	.chip-btn-active {
		border-color: rgba(11, 138, 164, 0.45);
		background: rgba(11, 138, 164, 0.14);
	}

	.chip-btn-soft {
		background: rgba(236, 106, 31, 0.08);
		border-color: rgba(236, 106, 31, 0.22);
	}

	.status-banner {
		margin-top: 16px;
		padding: 12px 14px;
		border-radius: 14px;
		border: 1px solid var(--line);
		line-height: 1.55;
	}

	.status-banner-info {
		background: rgba(11, 138, 164, 0.08);
		border-color: rgba(11, 138, 164, 0.2);
	}

	.status-banner-ok {
		background: rgba(13, 134, 80, 0.1);
		border-color: rgba(13, 134, 80, 0.24);
	}

	.status-banner-warn {
		background: rgba(201, 113, 17, 0.12);
		border-color: rgba(201, 113, 17, 0.24);
	}

	.status-banner-fail {
		background: rgba(188, 38, 38, 0.1);
		border-color: rgba(188, 38, 38, 0.24);
	}

	.result-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 12px;
	}

	.result-card {
		min-width: 0;
		display: grid;
		gap: 10px;
	}

	.result-copy {
		line-height: 1.7;
		white-space: pre-wrap;
		word-break: break-word;
	}

	.result-strong {
		font-weight: 700;
	}

	.evidence-list,
	.document-list {
		display: grid;
		gap: 10px;
	}

	.evidence-item,
	.document-item {
		padding: 12px;
		border-radius: 12px;
		border: 1px solid var(--line);
		background: rgba(255, 255, 255, 0.72);
		display: grid;
		gap: 6px;
	}

	.compact-list {
		margin-top: 0;
	}

	.guidance-diagnosis {
		margin-top: 0;
		color: var(--ink);
	}

	.guidance-match-list {
		gap: 8px;
	}

	.guidance-actions {
		padding-top: 4px;
	}

	.question-memory {
		margin-top: 0;
		max-width: 460px;
		text-align: right;
		word-break: break-word;
	}

	@media (max-width: 920px) {
		.result-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
