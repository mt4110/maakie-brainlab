describe('dashboard smoke', () => {
	it('loads overview and opens the consensus page', () => {
		cy.visit('/');
		cy.get('h1').should('be.visible');
		cy.contains('nav a', '概要').should('be.visible');

		cy.get('nav a[href="/consensus-il"]').click();
		cy.url().should('include', '/consensus-il');
		cy.get('h1').should('be.visible');
		cy.get('button')
			.contains(/Run Consensus|Consensus を実行|Running...|実行中.../)
			.should('be.visible');

		cy.get('nav a[href="/chat-lab"]').click();
		cy.url().should('include', '/chat-lab');
		cy.get('h1').should('be.visible');
		cy.get('button')
			.contains(/Send|送信/)
			.should('be.visible');
	});
});
