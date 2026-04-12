import path from 'node:path';

import { afterEach, describe, expect, it } from 'vitest';

import { REPO_ROOT } from './fs';
import {
	resolveGemmaLabPython,
	resolveGemmaLabRoot,
	resolveGemmaModelId,
	resolveLocalModelBackend,
	resolveLocalModelName,
	resolveLocalModelRuntimeLabel,
	resolveOpenAiModelName
} from './local-model';

const ORIGINAL_ENV = {
	IL_COMPILE_MODEL_BACKEND: process.env.IL_COMPILE_MODEL_BACKEND,
	LOCAL_MODEL_BACKEND: process.env.LOCAL_MODEL_BACKEND,
	LOCAL_GGUF_MODEL: process.env.LOCAL_GGUF_MODEL,
	GEMMA_MODEL_ID: process.env.GEMMA_MODEL_ID,
	GEMMA_LAB_ROOT: process.env.GEMMA_LAB_ROOT,
	GEMMA_LAB_PYTHON: process.env.GEMMA_LAB_PYTHON,
	OPENAI_API_BASE: process.env.OPENAI_API_BASE
};

function restoreEnv(name: keyof typeof ORIGINAL_ENV, value: string | undefined) {
	if (value === undefined) {
		delete process.env[name];
		return;
	}
	process.env[name] = value;
}

afterEach(() => {
	restoreEnv('IL_COMPILE_MODEL_BACKEND', ORIGINAL_ENV.IL_COMPILE_MODEL_BACKEND);
	restoreEnv('LOCAL_MODEL_BACKEND', ORIGINAL_ENV.LOCAL_MODEL_BACKEND);
	restoreEnv('LOCAL_GGUF_MODEL', ORIGINAL_ENV.LOCAL_GGUF_MODEL);
	restoreEnv('GEMMA_MODEL_ID', ORIGINAL_ENV.GEMMA_MODEL_ID);
	restoreEnv('GEMMA_LAB_ROOT', ORIGINAL_ENV.GEMMA_LAB_ROOT);
	restoreEnv('GEMMA_LAB_PYTHON', ORIGINAL_ENV.GEMMA_LAB_PYTHON);
	restoreEnv('OPENAI_API_BASE', ORIGINAL_ENV.OPENAI_API_BASE);
});

describe('local-model resolvers', () => {
	it('defaults to the existing openai-compatible backend', () => {
		process.env.IL_COMPILE_MODEL_BACKEND = '';
		process.env.LOCAL_MODEL_BACKEND = 'openai_compat';
		process.env.LOCAL_GGUF_MODEL = '';
		process.env.OPENAI_API_BASE = 'http://127.0.0.1:11434/v1';

		expect(resolveLocalModelBackend()).toBe('openai_compat');
		expect(resolveOpenAiModelName()).toBe('Qwen2.5-7B-Instruct');
		expect(resolveLocalModelName()).toBe('Qwen2.5-7B-Instruct');
		expect(resolveLocalModelRuntimeLabel()).toBe('http://127.0.0.1:11434/v1');
	});

	it('switches to gemma-lab when requested', () => {
		process.env.IL_COMPILE_MODEL_BACKEND = '';
		process.env.LOCAL_MODEL_BACKEND = 'gemma_lab';
		process.env.GEMMA_MODEL_ID = 'google/gemma-4-E2B-it';

		expect(resolveLocalModelBackend()).toBe('gemma_lab');
		expect(resolveGemmaModelId()).toBe('google/gemma-4-E2B-it');
		expect(resolveLocalModelName()).toBe('google/gemma-4-E2B-it');
		expect(resolveLocalModelRuntimeLabel()).toBe('gemma-lab direct');
	});

	it('derives gemma-lab paths from env or sibling repo defaults', () => {
		process.env.GEMMA_LAB_ROOT = '';
		process.env.GEMMA_LAB_PYTHON = '';
		expect(resolveGemmaLabRoot()).toBe(path.resolve(REPO_ROOT, '..', 'gemma-lab'));
		expect(resolveGemmaLabPython()).toBe(
			path.join(path.resolve(REPO_ROOT, '..', 'gemma-lab'), '.venv', 'bin', 'python')
		);

		process.env.GEMMA_LAB_ROOT = '/tmp/custom-gemma-lab';
		process.env.GEMMA_LAB_PYTHON = '/tmp/custom-gemma-lab/.venv/bin/python';
		expect(resolveGemmaLabRoot()).toBe('/tmp/custom-gemma-lab');
		expect(resolveGemmaLabPython()).toBe('/tmp/custom-gemma-lab/.venv/bin/python');
	});

	it('expands tilde-prefixed gemma root overrides', () => {
		process.env.GEMMA_LAB_ROOT = '~/custom-gemma-lab';
		expect(resolveGemmaLabRoot()).toBe(path.join(process.env.HOME || '', 'custom-gemma-lab'));
	});

	it('resolves relative gemma root overrides against the repo root', () => {
		process.env.GEMMA_LAB_ROOT = '../gemma-lab';
		expect(resolveGemmaLabRoot()).toBe(path.resolve(REPO_ROOT, '..', 'gemma-lab'));
	});

	it('preserves PATH-based gemma python overrides', () => {
		process.env.GEMMA_LAB_PYTHON = 'python3';
		expect(resolveGemmaLabPython()).toBe('python3');
	});

	it('resolves relative gemma python overrides against the repo root', () => {
		process.env.GEMMA_LAB_PYTHON = '../gemma-lab/.venv/bin/python';
		expect(resolveGemmaLabPython()).toBe(
			path.resolve(REPO_ROOT, '../gemma-lab/.venv/bin/python')
		);
	});

	it('lets LOCAL_MODEL_BACKEND override IL_COMPILE_MODEL_BACKEND', () => {
		process.env.LOCAL_MODEL_BACKEND = 'openai_compat';
		process.env.IL_COMPILE_MODEL_BACKEND = 'gemma_lab';
		expect(resolveLocalModelBackend()).toBe('openai_compat');
	});

	it('falls back to IL_COMPILE_MODEL_BACKEND when LOCAL_MODEL_BACKEND is empty', () => {
		process.env.LOCAL_MODEL_BACKEND = '';
		process.env.IL_COMPILE_MODEL_BACKEND = 'gemma_lab';
		expect(resolveLocalModelBackend()).toBe('gemma_lab');
	});

	it('rejects unsupported backend values', () => {
		process.env.LOCAL_MODEL_BACKEND = 'not_real_backend';
		expect(() => resolveLocalModelBackend()).toThrow(
			'Expected one of: openai_compat, gemma_lab.'
		);
	});
});
