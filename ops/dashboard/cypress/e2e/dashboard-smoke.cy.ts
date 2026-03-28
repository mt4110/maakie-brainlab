describe('dashboard smoke', () => {
	it('loads the simplified surfaces and opens ops when needed', () => {
		cy.visit('/');
		cy.get('h1').should('be.visible');
		cy.contains('nav a', '資料').should('be.visible');
		cy.contains('nav a', '質問').click();
		cy.url().should('include', '/questions');
		cy.get('h1').should('contain.text', '質問');

		cy.get('nav a[href="/evidence"]').click();
		cy.url().should('include', '/evidence');
		cy.get('h1').should('be.visible');

		cy.get('a[href="/ops"]').contains('Ops').click();
		cy.url().should('include', '/ops');
		cy.get('h1').should('be.visible');
		cy.get('a[href="/ops/overview"]').should('be.visible');
		cy.get('a[href="/chat-lab"]').should('be.visible');
	});
});
