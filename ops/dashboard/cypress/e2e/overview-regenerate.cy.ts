function mockOverview() {
	return {
		generatedAt: '2026-03-03T04:00:00.000Z',
		repoRoot: '/tmp/repo',
		health: { pass: 5, warn: 0, fail: 0, missing: 0 },
		pipelines: []
	};
}

describe('overview regenerate actions', () => {
	it('runs rag regenerate and shows progress/result', () => {
		cy.intercept('GET', '**/api/dashboard/overview*', {
			statusCode: 200,
			body: mockOverview()
		}).as('overview');

		cy.intercept('POST', '**/api/dashboard/run', {
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
						stdout: 'ok',
						stderr: ''
					}
				]
			}
		}).as('runRag');

		cy.visit('/');
		cy.wait(200);
		cy.get('[data-testid="regen-rag"]')
			.should('be.visible')
			.scrollIntoView()
			.click({ force: true });

		cy.wait('@runRag').its('request.body.pipeline').should('eq', 'rag');
		cy.wait('@overview');
		cy.get('[data-testid="run-progress"]')
			.contains(/PASS|FAIL/)
			.should('be.visible');
		cy.contains('p', /PASS 1/).should('be.visible');
		cy.contains('summary', 'rag').should('be.visible');
	});

	it('runs ml regenerate and renders ml log row', () => {
		cy.intercept('GET', '**/api/dashboard/overview*', {
			statusCode: 200,
			body: mockOverview()
		}).as('overview');

		cy.intercept('POST', '**/api/dashboard/run', {
			statusCode: 200,
			body: {
				status: 'PASS',
				results: [
					{
						pipeline: 'ml',
						command: ['python3', 'scripts/ops/s25_ml_experiment.py'],
						status: 'PASS',
						exitCode: 0,
						startedAt: '2026-03-03T04:01:10.000Z',
						endedAt: '2026-03-03T04:01:11.000Z',
						durationMs: 1000,
						runDir: null,
						stdout: 'ok',
						stderr: ''
					}
				]
			}
		}).as('runMl');

		cy.visit('/');
		cy.wait(200);
		cy.get('[data-testid="regen-ml"]')
			.should('be.visible')
			.scrollIntoView()
			.click({ force: true });

		cy.wait('@runMl').its('request.body.pipeline').should('eq', 'ml');
		cy.wait('@overview');
		cy.get('[data-testid="run-progress"]')
			.contains(/PASS|FAIL/)
			.should('be.visible');
		cy.contains('summary', 'ml').should('be.visible');
		cy.contains('div.path', 'scripts/ops/s25_ml_experiment.py').should('be.visible');
	});
});
