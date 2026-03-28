<script lang="ts">
	import { getContext } from 'svelte';

	import { I18N_CONTEXT_KEY, type LocaleState } from '$lib/i18n';

	const localeState = getContext<LocaleState>(I18N_CONTEXT_KEY);

	function tx(ja: string, en: string): string {
		return localeState.value === 'ja' ? ja : en;
	}

	const answerBlocks = [
		{
			ja: '答え',
			en: 'Answer',
			copyJa: '最初に短く結論を返す。',
			copyEn: 'Return a short conclusion first.'
		},
		{
			ja: '根拠',
			en: 'Evidence',
			copyJa: 'どの資料のどの断片を使ったか見せる。',
			copyEn: 'Show which document fragments supported the answer.'
		},
		{
			ja: '使われた資料',
			en: 'Documents used',
			copyJa: '参照した資料へ戻れる導線を残す。',
			copyEn: 'Keep a clear path back to the cited documents.'
		},
		{
			ja: '分からないこと',
			en: 'Unknowns',
			copyJa: '足りない資料や質問の曖昧さを明示する。',
			copyEn: 'State missing documents or ambiguity explicitly.'
		}
	];
</script>

<div class="surface-stack">
	<section class="hero">
		<article class="panel panel-strong">
			<p class="eyebrow">{tx('質問', 'Questions')}</p>
			<h1 class="title">
				{tx(
					'質問面は、答えと根拠に集中する入口へ整理中です。',
					'The question surface is being reduced to answers and evidence.'
				)}
			</h1>
			<p class="muted">
				{tx(
					'Phase 1 では用語と導線だけを正し、Phase 2 で入力・回答・不明表示をこの面へ寄せます。RAG や lab 用語は main path から外します。',
					'Phase 1 fixes the language and navigation. Phase 2 will move input, answer, and unknown handling onto this surface. RAG and lab jargon stays off the main path.'
				)}
			</p>
			<div class="inline-actions">
				<a class="btn-link btn-primary" href="/chat-lab"
					>{tx('暫定の質問フローを開く', 'Open the transitional question flow')}</a
				>
				<a class="btn-link btn-ghost" href="/ops">{tx('Ops で内部面を見る', 'Open internal surfaces in Ops')}</a>
			</div>
		</article>
		<article class="panel">
			<p class="eyebrow">{tx('不明時の扱い', 'When the answer is unknown')}</p>
			<ul class="flat-list">
				<li>
					{tx(
						'分からないときは「分からない」と明示する。',
						'Say clearly when the answer is unknown.'
					)}
				</li>
				<li>
					{tx(
						'何が足りないかを出す。',
						'Explain what is missing.'
					)}
				</li>
				<li>
					{tx(
						'次の一手を出す。資料追加、更新、質問具体化。',
						'Suggest the next action: add documents, refresh the index, or make the question more specific.'
					)}
				</li>
			</ul>
		</article>
	</section>

	<section class="panel">
		<div class="section-head">
			<div>
				<p class="eyebrow">{tx('理想の返し方', 'Ideal response shape')}</p>
				<h2 class="section-title">
					{tx(
						'通常ユーザーには、内部契約ではなく4つの読みやすい塊だけを見せます。',
						'Normal users should only see four readable blocks, not internal contracts.'
					)}
				</h2>
			</div>
		</div>
		<div class="card-grid">
			{#each answerBlocks as block}
				<article class="panel surface-card">
					<h3 class="pipeline-title">{tx(block.ja, block.en)}</h3>
					<p class="section-copy">{tx(block.copyJa, block.copyEn)}</p>
				</article>
			{/each}
		</div>
	</section>
</div>
