describe('phase 1 surface simplification', () => {
	it('keeps internal routes out of the main nav and reachable via ops', () => {
		cy.visit('/');
		cy.contains('nav a', '概要').should('not.exist');
		cy.contains('nav a', '資料').should('be.visible');
		cy.contains('nav a', '質問').should('be.visible');
		cy.contains('nav a', '根拠').should('be.visible');

		cy.get('a[href="/ops"]').click();
		cy.url().should('include', '/ops');
		cy.get('a[href="/prompt-trace"]').should('be.visible');
		cy.get('a[href="/rag-lab"]').should('be.visible');
		cy.get('a[href="/langchain-lab"]').should('be.visible');
	});
});
