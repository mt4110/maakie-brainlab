import { describe, expect, it } from 'vitest';

import { classifyChatRunFailure, presentQuestionRun } from './presenter';
import type { ChatRunResponse } from '$lib/server/types';

function makePayload(input: Partial<ChatRunResponse>): ChatRunResponse {
	return {
		status: 'PASS',
		assistantMessage: '',
		ragSuggestions: [],
		model: 'Qwen2.5-7B-Instruct',
		apiBase: 'http://127.0.0.1:11434/v1',
		...input
	};
}

describe('classifyChatRunFailure', () => {
	it('detects backend connectivity failures', () => {
		expect(
			classifyChatRunFailure(
				'openai-compatible endpoint not found; attempts=[http://127.0.0.1:11434/v1/chat/completions -> network_error: fetch failed]'
			)
		).toBe('backend_unavailable');
	});

	it('keeps generic server failures separate', () => {
		expect(classifyChatRunFailure('Unexpected sqlite error while writing logs')).toBe(
			'server_failure'
		);
	});

	it('treats gemma runtime setup failures as backend unavailable', () => {
		expect(classifyChatRunFailure('gemma-lab root not found: /tmp/gemma-lab')).toBe(
			'backend_unavailable'
		);
	});
});

describe('presentQuestionRun', () => {
	it('keeps answer and evidence when matching sources exist', () => {
		const presentation = presentQuestionRun(
			makePayload({
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
			})
		);

		expect(presentation.kind).toBe('answer');
		expect(presentation.answer).toContain('3 面');
		expect(presentation.evidence).toHaveLength(1);
		expect(presentation.documentsUsed).toHaveLength(1);
		expect(presentation.notices).toContain('verify_before_reuse');
	});

	it('downgrades unsupported answers to unknown when no document matches exist', () => {
		const presentation = presentQuestionRun(
			makePayload({
				assistantMessage: '現在、登録者数が最も多いYouTubeチャンネルは T-Series です。'
			})
		);

		expect(presentation.kind).toBe('unknown');
		expect(presentation.answer).toBe('');
		expect(presentation.evidence).toHaveLength(0);
		expect(presentation.documentsUsed).toHaveLength(0);
		expect(presentation.notices).toContain('no_matching_documents');
	});
});
