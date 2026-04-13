import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const {
	postOpenAiCompatChatMock,
	existsSyncMock,
	readFileSyncMock,
	originalRepoRoot
} = vi.hoisted(() => {
	const original = process.env.MAAKIE_REPO_ROOT;
	process.env.MAAKIE_REPO_ROOT = '../..';
	return {
		postOpenAiCompatChatMock: vi.fn(),
		existsSyncMock: vi.fn(() => true),
		readFileSyncMock: vi.fn(() => 'OPENAI_API_KEY=from-dotenv\n'),
		originalRepoRoot: original
	};
});

vi.mock('node:fs', async (importOriginal) => {
	const actual = await importOriginal<typeof import('node:fs')>();
	return {
		...actual,
		existsSync: existsSyncMock,
		readFileSync: readFileSyncMock
	};
});

vi.mock('./openai-compat', async (importOriginal) => {
	const actual = await importOriginal<typeof import('./openai-compat')>();
	return {
		...actual,
		postOpenAiCompatChat: postOpenAiCompatChatMock
	};
});

import { postLocalModelChat } from './local-model';

const ORIGINAL_ENV = {
	MAAKIE_REPO_ROOT: originalRepoRoot,
	IL_COMPILE_MODEL_BACKEND: process.env.IL_COMPILE_MODEL_BACKEND,
	LOCAL_MODEL_BACKEND: process.env.LOCAL_MODEL_BACKEND,
	OPENAI_API_KEY: process.env.OPENAI_API_KEY
};

function restoreEnv(name: keyof typeof ORIGINAL_ENV, value: string | undefined) {
	if (value === undefined) {
		delete process.env[name];
		return;
	}
	process.env[name] = value;
}

beforeEach(() => {
	postOpenAiCompatChatMock.mockReset();
	existsSyncMock.mockReset();
	readFileSyncMock.mockReset();
	existsSyncMock.mockReturnValue(true);
	readFileSyncMock.mockReturnValue('OPENAI_API_KEY=from-dotenv\n');
	process.env.IL_COMPILE_MODEL_BACKEND = '';
	process.env.LOCAL_MODEL_BACKEND = 'openai_compat';
	delete process.env.OPENAI_API_KEY;
	postOpenAiCompatChatMock.mockResolvedValue({
		content: 'ok',
		resolvedUrl: 'http://127.0.0.1:11434/v1/chat/completions'
	});
});

afterEach(() => {
	restoreEnv('MAAKIE_REPO_ROOT', ORIGINAL_ENV.MAAKIE_REPO_ROOT);
	restoreEnv('IL_COMPILE_MODEL_BACKEND', ORIGINAL_ENV.IL_COMPILE_MODEL_BACKEND);
	restoreEnv('LOCAL_MODEL_BACKEND', ORIGINAL_ENV.LOCAL_MODEL_BACKEND);
	restoreEnv('OPENAI_API_KEY', ORIGINAL_ENV.OPENAI_API_KEY);
});

describe('postLocalModelChat', () => {
	it('uses dashboard env OPENAI_API_KEY when request apiKey is empty', async () => {
		await postLocalModelChat({
			apiKey: '',
			model: 'Qwen2.5-7B-Instruct',
			messages: [{ role: 'user', content: 'hello' }]
		});

		expect(postOpenAiCompatChatMock).toHaveBeenCalledWith(
			expect.objectContaining({
				apiKey: 'from-dotenv'
			})
		);
	});
});
