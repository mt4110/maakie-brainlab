import { EventEmitter } from 'node:events';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { spawnMock, existsSyncMock, readFileSyncMock, originalRepoRoot } = vi.hoisted(() => {
	const original = process.env.MAAKIE_REPO_ROOT;
	process.env.MAAKIE_REPO_ROOT = '../..';
	return {
		spawnMock: vi.fn(),
		existsSyncMock: vi.fn(() => true),
		readFileSyncMock: vi.fn(() => ''),
		originalRepoRoot: original
	};
});

vi.mock('node:child_process', async (importOriginal) => {
	const actual = await importOriginal<typeof import('node:child_process')>();
	return {
		...actual,
		spawn: spawnMock
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

import { probeGemmaLabRuntime } from './local-model';

class FakeStream extends EventEmitter {}

class FakeChild extends EventEmitter {
	stdout = new FakeStream();
	stderr = new FakeStream();
	stdin = {
		write: vi.fn(),
		end: vi.fn()
	};
	kill = vi.fn(() => true);
}

const ORIGINAL_ENV = {
	MAAKIE_REPO_ROOT: originalRepoRoot,
	LOCAL_MODEL_BACKEND: process.env.LOCAL_MODEL_BACKEND,
	GEMMA_MODEL_ID: process.env.GEMMA_MODEL_ID,
	GEMMA_LAB_ROOT: process.env.GEMMA_LAB_ROOT,
	GEMMA_LAB_PYTHON: process.env.GEMMA_LAB_PYTHON
};

function restoreEnv(name: keyof typeof ORIGINAL_ENV, value: string | undefined) {
	if (value === undefined) {
		delete process.env[name];
		return;
	}
	process.env[name] = value;
}

beforeEach(() => {
	vi.useFakeTimers();
	spawnMock.mockReset();
	existsSyncMock.mockReset();
	readFileSyncMock.mockReset();
	existsSyncMock.mockReturnValue(true);
	readFileSyncMock.mockReturnValue('');
	process.env.LOCAL_MODEL_BACKEND = 'gemma_lab';
	process.env.GEMMA_MODEL_ID = 'google/gemma-4-E2B-it';
	process.env.GEMMA_LAB_ROOT = '/tmp/gemma-lab';
	process.env.GEMMA_LAB_PYTHON = 'python3';
});

afterEach(() => {
	restoreEnv('MAAKIE_REPO_ROOT', ORIGINAL_ENV.MAAKIE_REPO_ROOT);
	restoreEnv('LOCAL_MODEL_BACKEND', ORIGINAL_ENV.LOCAL_MODEL_BACKEND);
	restoreEnv('GEMMA_MODEL_ID', ORIGINAL_ENV.GEMMA_MODEL_ID);
	restoreEnv('GEMMA_LAB_ROOT', ORIGINAL_ENV.GEMMA_LAB_ROOT);
	restoreEnv('GEMMA_LAB_PYTHON', ORIGINAL_ENV.GEMMA_LAB_PYTHON);
	vi.useRealTimers();
});

describe('gemma bridge timeout handling', () => {
	it('fails fast on timeout without waiting for close', async () => {
		const child = new FakeChild();
		spawnMock.mockReturnValue(child);

		const probePromise = probeGemmaLabRuntime();

		await vi.advanceTimersByTimeAsync(20 * 60 * 1000);
		await expect(probePromise).resolves.toMatchObject({
			status: 'error',
			error: 'gemma bridge timed out after 20 minutes'
		});
		expect(child.kill).toHaveBeenNthCalledWith(1, 'SIGTERM');

		await vi.advanceTimersByTimeAsync(5 * 1000);
		expect(child.kill).toHaveBeenNthCalledWith(2, 'SIGKILL');
	});

	it('treats non-zero exits with parsed errors as failures', async () => {
		const child = new FakeChild();
		spawnMock.mockReturnValue(child);

		const probePromise = probeGemmaLabRuntime();

		child.stdout.emit(
			'data',
			'{"status":"error","error":"ModuleNotFoundError: missing gemma runtime"}'
		);
		child.emit('close', 1);

		await expect(probePromise).resolves.toMatchObject({
			status: 'error',
			error: 'gemma bridge failed: ModuleNotFoundError: missing gemma runtime'
		});
	});
});
