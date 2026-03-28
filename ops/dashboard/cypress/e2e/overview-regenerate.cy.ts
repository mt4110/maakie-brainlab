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

	it('can trigger overview regeneration and render status/logs', () => {
		// Mock the overview data loaded by /ops/overview
		cy.intercept('GET', '/api/dashboard/overview', {
			statusCode: 200,
			body: {
				lastRunStatus: 'idle',
				lastRunAt: null,
			},
		}).as('getOverview');

		// Mock the pipeline run endpoint that drives the regeneration flow
		cy.intercept('POST', '/api/dashboard/run', {
			statusCode: 200,
			body: {
				status: 'completed',
				message: 'Regeneration complete',
				logs: [
					'Starting regeneration pipeline...',
					'Fetching latest data...',
					'Regeneration complete.',
				],
			},
		}).as('runOverview');

		// Visit the overview page in ops and wait for initial overview data
		cy.visit('/ops/overview');
		cy.wait('@getOverview');

		// Trigger regeneration via a button whose data-testid starts with "regen-"
		cy.get('[data-testid^="regen-"]').click();

		// Wait for the mocked run request to complete
		cy.wait('@runOverview');

		// Assert that the regeneration status is rendered
		cy.get('[data-testid="regen-status"]').should('contain', 'Regeneration complete');

		// Assert that logs from the mocked run are rendered in the UI
		cy.get('[data-testid="regen-logs"]').within(() => {
			cy.contains('Starting regeneration pipeline...').should('be.visible');
			cy.contains('Regeneration complete.').should('be.visible');
		});
	});
});
