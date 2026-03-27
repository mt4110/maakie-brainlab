import { defineConfig } from 'cypress';

export default defineConfig({
	video: false,
	e2e: {
		baseUrl: 'http://127.0.0.1:3033',
		specPattern: 'cypress/e2e/**/*.cy.ts',
		supportFile: false
	}
});
