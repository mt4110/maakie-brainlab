describe('questions main path', () => {
	it('keeps the question flow on /questions and shows the four blocks', () => {
		cy.visit('/questions');
		cy.get('h1').should('contain.text', '質問');

		cy.contains('.meta-card', /有効な資料|Enabled documents/)
			.find('.meta-value')
			.invoke('text')
			.then((rawCount) => {
				const enabledCount = Number(rawCount.trim());

				if (enabledCount > 0) {
					cy.intercept('POST', '/api/dashboard/chat/run', {
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
				}

				cy.get('textarea').type('main path は何面？');
				cy.contains('button', /質問する|Ask/).click();

				if (enabledCount > 0) {
					cy.wait('@chatRun');
					cy.url().should('include', '/questions');
					cy.contains('.result-card', '答え').should('contain.text', '3 面');
					cy.contains('.result-card', '根拠').should(
						'contain.text',
						'Official Product Requirements'
					);
					cy.contains('.result-card', '使われた資料').should('contain.text', 'PRODUCT.md');
					cy.contains('.result-card', '分からないこと / 注意点').should(
						'contain.text',
						'Evidence'
					);
				} else {
					cy.contains('.result-card', '答え').should('contain.text', '資料が 0 件');
					cy.contains('.result-card', '分からないこと / 注意点').should(
						'contain.text',
						'Documents'
					);
				}

				cy.get('a[href="/chat-lab"]').should('not.exist');
			});
	});
});
