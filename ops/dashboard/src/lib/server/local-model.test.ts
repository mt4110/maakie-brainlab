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
	LOCAL_MODEL_BACKEND: process.env.LOCAL_MODEL_BACKEND,
	LOCAL_GGUF_MODEL: process.env.LOCAL_GGUF_MODEL,
	GEMMA_MODEL_ID: process.env.GEMMA_MODEL_ID,
	GEMMA_LAB_ROOT: process.env.GEMMA_LAB_ROOT,
	GEMMA_LAB_PYTHON: process.env.GEMMA_LAB_PYTHON,
	OPENAI_API_BASE: process.env.OPENAI_API_BASE
};

afterEach(() => {
	process.env.LOCAL_MODEL_BACKEND = ORIGINAL_ENV.LOCAL_MODEL_BACKEND;
	process.env.LOCAL_GGUF_MODEL = ORIGINAL_ENV.LOCAL_GGUF_MODEL;
	process.env.GEMMA_MODEL_ID = ORIGINAL_ENV.GEMMA_MODEL_ID;
	process.env.GEMMA_LAB_ROOT = ORIGINAL_ENV.GEMMA_LAB_ROOT;
	process.env.GEMMA_LAB_PYTHON = ORIGINAL_ENV.GEMMA_LAB_PYTHON;
	process.env.OPENAI_API_BASE = ORIGINAL_ENV.OPENAI_API_BASE;
});

describe('local-model resolvers', () => {
	it('defaults to the existing openai-compatible backend', () => {
		process.env.LOCAL_MODEL_BACKEND = 'openai_compat';
		process.env.LOCAL_GGUF_MODEL = '';
		process.env.OPENAI_API_BASE = 'http://127.0.0.1:11434/v1';

		expect(resolveLocalModelBackend()).toBe('openai_compat');
		expect(resolveOpenAiModelName()).toBe('Qwen2.5-7B-Instruct');
		expect(resolveLocalModelName()).toBe('Qwen2.5-7B-Instruct');
		expect(resolveLocalModelRuntimeLabel()).toBe('http://127.0.0.1:11434/v1');
	});

	it('switches to gemma-lab when requested', () => {
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

	it('preserves PATH-based gemma python overrides', () => {
		process.env.GEMMA_LAB_PYTHON = 'python3';
		expect(resolveGemmaLabPython()).toBe('python3');
	});
});
