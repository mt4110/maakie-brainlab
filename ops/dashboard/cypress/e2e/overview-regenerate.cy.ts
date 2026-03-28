function mockOverview() {
	return {
		generatedAt: '2026-03-03T04:00:00.000Z',
		repoRoot: '/tmp/repo',
		health: { pass: 5, warn: 0, fail: 0, missing: 0 },
		pipelines: [
			{
				key: 'rag',
				title: 'RAG',
				artifactPath: 'docs/evidence/s25-08/rag_tuning_latest.json',
				schema: 'rag',
				status: 'PASS',
				capturedAt: '2026-03-03T04:00:00.000Z',
				summary: 'RAG tuning snapshot',
				metrics: [{ label: 'Hit Rate', value: '92%' }]
			}
		]
	};
}

describe('phase 1 surface simplification', () => {
	it('keeps internal routes out of the main nav and reachable via ops', () => {
		cy.visit('/');
		cy.contains('nav a', '概要').should('not.exist');
		cy.contains('nav a', '資料').should('be.visible');
		cy.contains('nav a', '質問').should('be.visible');
		cy.contains('nav a', '根拠').should('be.visible');

		cy.get('header .utility-link[href="/ops"]').click();
		cy.url().should('include', '/ops');
		cy.get('a[href="/prompt-trace"]').should('be.visible');
		cy.get('a[href="/rag-lab"]').should('be.visible');
		cy.get('a[href="/langchain-lab"]').should('be.visible');
	});
	it('runs regeneration from ops overview without exposing a broken status flow', () => {
		cy.intercept('GET', '**/api/dashboard/overview*', {
			statusCode: 200,
			body: mockOverview()
		}).as('overviewReload');

		cy.intercept('POST', '**/api/dashboard/run', (req) => {
			expect(req.body.pipeline).to.eq('rag');
			req.reply({
				delay: 200,
				statusCode: 200,
				body: {
					status: 'PASS',
					results: [
						{
							pipeline: 'rag',
							command: ['python3', 'scripts/ops/s25_rag_tuning_loop.py'],
							status: 'PASS',
							exitCode: 0,
							startedAt: '2026-03-03T04:00:10.000Z',
							endedAt: '2026-03-03T04:00:11.000Z',
							durationMs: 1000,
							runDir: null,
							stdout: 'Starting regeneration pipeline...\nRegeneration complete.',
							stderr: ''
						}
					]
				}
			});
		}).as('runRag');

		cy.visit('/ops/overview');
		cy.get('[data-testid="reload-overview"]').should('not.be.disabled');
		cy.get('[data-testid="regen-rag"]').should('be.visible').and('not.be.disabled').click();
		cy.get('[data-testid="reload-overview"]').should('be.disabled');

		cy.wait('@runRag');
		cy.wait('@overviewReload');

		cy.get('[data-testid="run-progress"]').should('contain.text', 'PASS');
		cy.contains('h2', '直近の実行結果').should('be.visible');
		cy.contains('p', /PASS 1/).should('be.visible');
		cy.contains('details summary', 'rag').should('be.visible').click();
		cy.contains('pre', 'Regeneration complete.').should('exist');
	});
});
