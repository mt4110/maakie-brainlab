import { afterEach, describe, expect, it } from 'vitest';

import { chatCompletionUrlCandidates, resolveOpenAiCompatApiBase } from './openai-compat';

const ORIGINAL_OPENAI_API_BASE = process.env.OPENAI_API_BASE;

afterEach(() => {
	process.env.OPENAI_API_BASE = ORIGINAL_OPENAI_API_BASE;
});

describe('openai-compat', () => {
	it('builds /v1 and non-/v1 fallback URLs', () => {
		expect(chatCompletionUrlCandidates('http://127.0.0.1:8080/v1')).toEqual([
			'http://127.0.0.1:8080/v1/chat/completions',
			'http://127.0.0.1:8080/chat/completions'
		]);
		expect(chatCompletionUrlCandidates('http://127.0.0.1:8080')).toEqual([
			'http://127.0.0.1:8080/chat/completions',
			'http://127.0.0.1:8080/v1/chat/completions'
		]);
	});

	it('normalizes base URL when chat path is already included', () => {
		expect(chatCompletionUrlCandidates('http://127.0.0.1:8080/v1/chat/completions')).toEqual([
			'http://127.0.0.1:8080/v1/chat/completions',
			'http://127.0.0.1:8080/chat/completions'
		]);
	});

	it('resolves api base from env or default', () => {
		process.env.OPENAI_API_BASE = 'http://localhost:9999/v1';
		expect(resolveOpenAiCompatApiBase('')).toBe('http://localhost:9999/v1');
		process.env.OPENAI_API_BASE = '';
		expect(resolveOpenAiCompatApiBase('')).toBe('http://127.0.0.1:11434/v1');
	});
});
