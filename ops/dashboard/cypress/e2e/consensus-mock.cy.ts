describe('consensus mocked run', () => {
	it('submits form and renders mocked consensus result/history', () => {
		const mockPrompt = 'モックで履歴登録テスト';
		const mockRecord = {
			id: 'mock-record-001',
			createdAt: '2026-02-28T09:30:00.000Z',
			prompt: mockPrompt,
			contract: {
				minAgents: 2,
				requiredEvidence: true,
				requiredGuards: true
			},
			guard: {
				passed: false,
				details: ['contract: requires >=2 PASS agents, got 1']
			},
			evidence: {
				refs: ['docs/evidence/dashboard/consensus_contract/mock.json#chunk-1']
			},
			result: {
				status: 'WARN',
				summary: 'pass=1/3, evidence=1',
				consensusText: 'Consensus summary:\n- [local] モック応答'
			},
			timeline: {
				totalMs: 321,
				localMs: 111,
				cliMs: 103,
				apiMs: 107
			},
			agents: [
				{
					agent: 'local',
					status: 'PASS',
					durationMs: 111,
					command: 'python3 src/ask.py ...',
					output: '- モック応答',
					error: '',
					evidenceRefs: ['docs/evidence/dashboard/consensus_contract/mock.json#chunk-1'],
					guardPassed: true
				},
				{
					agent: 'cli',
					status: 'FAIL',
					durationMs: 103,
					command: 'echo cli',
					output: '',
					error: 'mock fail',
					evidenceRefs: [],
					guardPassed: false
				},
				{
					agent: 'api',
					status: 'SKIP',
					durationMs: 0,
					command: 'skipped',
					output: '',
					error: 'mock skip',
					evidenceRefs: [],
					guardPassed: false
				}
			]
		};

		cy.intercept('POST', '/api/dashboard/consensus/run', (req) => {
			expect(String(req.body.prompt)).to.contain(mockPrompt);
			req.reply({
				statusCode: 200,
				body: {
					status: 'WARN',
					record: mockRecord
				}
			});
		}).as('consensusRun');

		cy.intercept('GET', '/api/dashboard/consensus/history*', {
			statusCode: 200,
			body: { items: [mockRecord] }
		}).as('consensusHistory');

		cy.visit('/consensus-il');
		cy.get('textarea').type('{selectall}{backspace}').type(mockPrompt);
		cy.get('button')
			.contains(/Run Consensus|Consensus を実行/)
			.click();

		cy.wait('@consensusRun');
		cy.wait('@consensusHistory');

		cy.get('h2').should('be.visible');
		cy.contains('span', 'WARN').should('be.visible');
		cy.contains('.snippet', 'Consensus summary:').should('be.visible');
		cy.contains('td', mockPrompt).should('be.visible');
	});
});
