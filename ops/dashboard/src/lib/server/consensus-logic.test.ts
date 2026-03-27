import { describe, expect, it } from 'vitest';

import {
	buildConsensusText,
	evaluateContract,
	evidenceRefsFromText,
	firstMeaningfulLine
} from './consensus-logic';
import type { ConsensusAgentResult, DashboardStatus } from './types';

function makeAgent(args: {
	agent: ConsensusAgentResult['agent'];
	status: DashboardStatus;
	output?: string;
}): ConsensusAgentResult {
	return {
		agent: args.agent,
		status: args.status,
		durationMs: 12,
		command: `run-${args.agent}`,
		output: args.output ?? '',
		error: '',
		evidenceRefs: [],
		guardPassed: args.status === 'PASS'
	};
}

describe('consensus-logic', () => {
	it('extracts chunk refs and urls from output text', () => {
		const text = [
			'結論: sample',
			'- docs/evidence/rag/_latest.json#chunk-10',
			'- docs/evidence/rag/_latest.json#chunk-10',
			'参照: https://example.com/paper',
			'https://example.com/paper',
			'https://example.org/path)'
		].join('\n');

		expect(evidenceRefsFromText(text)).toEqual([
			'docs/evidence/rag/_latest.json#chunk-10',
			'https://example.com/paper',
			'https://example.org/path'
		]);
	});

	it('returns first meaningful line by skipping boilerplate labels', () => {
		const text = [
			'結論: provisional',
			'根拠: docs/evidence/abc#chunk-1',
			'参照: https://example.com',
			'- 採用方針は retrieval-first にする'
		].join('\n');

		expect(firstMeaningfulLine(text)).toBe('採用方針は retrieval-first にする');
	});

	it('builds consensus text from PASS agents only', () => {
		const text = buildConsensusText([
			makeAgent({
				agent: 'local',
				status: 'PASS',
				output: '結論: ok\n- ローカルで再現できる'
			}),
			makeAgent({
				agent: 'cli',
				status: 'FAIL',
				output: '- CLI output'
			}),
			makeAgent({
				agent: 'api',
				status: 'PASS',
				output: '参照: https://example.com\n- API推奨はA/Bテスト先行'
			})
		]);

		expect(text).toContain('Consensus summary:');
		expect(text).toContain('- [local] ローカルで再現できる');
		expect(text).toContain('- [api] API推奨はA/Bテスト先行');
		expect(text).not.toContain('[cli]');
	});

	it('evaluates contract and guard into WARN when constraints fail', () => {
		const evaluated = evaluateContract({
			passAgents: 1,
			activeAgents: 3,
			evidenceCount: 0,
			guardDetails: ['cli: guard failed (empty output or execution failure)']
		});

		expect(evaluated.status).toBe('WARN');
		expect(evaluated.contract.minAgents).toBe(2);
		expect(evaluated.details).toContain('contract: requires >=2 PASS agents, got 1');
		expect(evaluated.details).toContain('contract: evidence refs are empty');
		expect(evaluated.details).toContain('contract: one or more guards failed');
		expect(evaluated.summary).toBe('pass=1/3, evidence=0');
	});
});
