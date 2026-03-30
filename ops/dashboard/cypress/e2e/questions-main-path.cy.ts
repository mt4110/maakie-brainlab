describe('questions main path', () => {
	let createdSourceIds: string[] = [];
	const seedSources = [
		{
			name: 'Official Product Requirements',
			description: 'Seed document for the /questions main path E2E.',
			path: 'PRODUCT.md',
			tags: ['product', 'cypress'],
			enabled: true
		},
		{
			name: 'Official System Architecture',
			description: 'Architecture seed document for the /questions main path E2E.',
			path: 'ARCHITECTURE.md',
			tags: ['architecture', 'cypress'],
			enabled: true
		}
	];

	const resultCard = (label: RegExp) =>
		cy.contains('.result-card .eyebrow', label).closest('.result-card');

	beforeEach(() => {
		createdSourceIds = [];
		cy.wrap(seedSources).each((item) => {
			cy.request('POST', '/api/dashboard/rag-sources', item)
				.its('body.item.id')
				.then((id) => {
					createdSourceIds.push(String(id));
				});
		})
	});

	afterEach(() => {
		if (createdSourceIds.length === 0) {
			return;
		}
		cy.wrap(createdSourceIds).each((id) => {
			cy.request('DELETE', `/api/dashboard/rag-sources/${id}`);
		});
		cy.then(() => {
			createdSourceIds = [];
		});
	});

	it('shows corpus-aware examples and keeps the answer on the same screen', () => {
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
		cy.contains('button', '指定しない').should('exist');
		cy.contains('button', 'Official Product Requirements').should('exist');
		cy.contains('button', 'Official Product Requirements の要点は？').click();
		cy.get('textarea').should('have.value', 'Official Product Requirements の要点は？');

		cy.contains('button', /^質問する$|^Ask$/).should('not.be.disabled').click();
		cy.wait('@chatRun')
			.its('request.body.selectedRagIds')
			.should('have.length', 1);
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

	it('diagnoses document-name mismatch and suggests better re-asks', () => {
		cy.intercept('POST', '**/api/dashboard/chat/run', {
			statusCode: 200,
			body: {
				status: 'PASS',
				assistantMessage: '現在の資料だけでは判断できません。',
				ragSuggestions: [],
				model: 'Qwen2.5-7B-Instruct',
				apiBase: 'http://127.0.0.1:11434/v1'
			}
		}).as('chatRun');

		cy.visit('/questions', {
			onBeforeLoad(win) {
				win.localStorage.setItem('dashboard.locale', 'ja');
			}
		});
		cy.document().its('documentElement.lang').should('eq', 'ja');
		cy.get('textarea').type('Product.mdでmain pathは何面に整理されている？');
		cy.contains('button', /^質問する$|^Ask$/).click();
		cy.wait('@chatRun');

		resultCard(/^分からないこと \/ 注意点$|^Unknowns \/ Cautions$/).within(() => {
			cy.contains('Product.md').should('exist');
			cy.contains('Official Product Requirements').should('exist');
			cy.contains('button', 'Official Product Requirementsでmain pathは何面に整理されている？').click();
		});
		cy.get('textarea').should(
			'have.value',
			'Official Product Requirementsでmain pathは何面に整理されている？'
		);
	});
});
