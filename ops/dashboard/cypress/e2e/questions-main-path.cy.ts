describe('questions main path', () => {
	let createdSourceId: string | null = null;

	const resultCard = (label: RegExp) =>
		cy.contains('.result-card .eyebrow', label).closest('.result-card');

	beforeEach(() => {
		cy.request('POST', '/api/dashboard/rag-sources', {
			name: 'Cypress Questions Main Path',
			description: 'Seed document for the /questions main path E2E.',
			path: 'PRODUCT.md',
			tags: ['product', 'cypress'],
			enabled: true
		})
			.its('body.item.id')
			.then((id) => {
				createdSourceId = String(id);
			});
	});

	afterEach(() => {
		if (!createdSourceId) {
			return;
		}
		cy.request('DELETE', `/api/dashboard/rag-sources/${createdSourceId}`);
		cy.then(() => {
			createdSourceId = null;
		});
	});

	it('keeps the question flow on /questions and shows the four blocks', () => {
		cy.intercept('POST', '**/api/dashboard/chat/run', {
			statusCode: 200,
			body: {
				status: 'PASS',
				assistantMessage: 'main path は Documents / Questions / Evidence の 3 面です。',
				ragSuggestions: [
					{
						id: 'official-001',
						name: 'Official Product Requirements',
						path: 'PRODUCT.md',
						tags: ['product'],
						score: 7,
						reason: 'name:product, selected'
					}
				],
				model: 'Qwen2.5-7B-Instruct',
				apiBase: 'http://127.0.0.1:11434/v1',
				inspector: {
					id: 'run-1',
					scope: 'chat-lab',
					source: 'chat-rag',
					status: 'PASS',
					createdAt: '2026-03-29T00:00:00.000Z',
					prompt: 'main path は何面？',
					outputText: 'main path は Documents / Questions / Evidence の 3 面です。',
					command: 'POST /api/dashboard/chat/run',
					model: 'Qwen2.5-7B-Instruct',
					apiBase: 'http://127.0.0.1:11434/v1',
					durationMs: 120,
					errorReason: '',
					metadata: {},
					messages: [],
					retrievals: [
						{
							seq: 0,
							sourceId: 'official-001',
							sourcePath: 'PRODUCT.md',
							chunkText: 'Official Product Requirements',
							score: 7,
							reason: 'name:product, selected'
						}
					],
					votes: []
				}
			}
		}).as('chatRun');

		cy.visit('/questions', {
			onBeforeLoad(win) {
				win.localStorage.setItem('dashboard.locale', 'ja');
			}
		});
		cy.document().its('documentElement.lang').should('eq', 'ja');
		cy.get('h1').should('contain.text', '質問');
		cy.contains('.meta-card', /有効な資料|Enabled documents/)
			.find('.meta-value')
			.should(($value) => {
				expect(Number($value.text().trim())).to.be.greaterThan(0);
			});

		cy.get('textarea').type('main path は何面？');
		cy.contains('button', /^質問する$|^Ask$/).should('not.be.disabled').click();

		cy.wait('@chatRun');
		cy.url().should('include', '/questions');
		resultCard(/^答え$|^Answer$/).should('contain.text', '3 面');
		resultCard(/^根拠$|^Evidence$/).should('contain.text', 'Official Product Requirements');
		resultCard(/^使われた資料$|^Documents used$/).should('contain.text', 'PRODUCT.md');
		resultCard(/^分からないこと \/ 注意点$|^Unknowns \/ Cautions$/).should(
			'contain.text',
			'Evidence'
		);
		cy.get('a[href="/chat-lab"]').should('not.exist');
	});
});
