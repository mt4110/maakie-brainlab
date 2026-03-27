import { existsSync } from 'node:fs';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

import { REPO_ROOT, repoJoin, walkFiles } from './fs';
import type { CommandRunResult, DashboardStatus, PipelineKey, PipelineRunResponse } from './types';

const COMMAND_TIMEOUT_MS = 20 * 60 * 1000;
const OUTPUT_LIMIT = 80_000;

function pythonExecutable(): string {
	const venvPython = repoJoin('.venv/bin/python');
	if (existsSync(venvPython)) {
		return venvPython;
	}
	return 'python3';
}

function toStatus(exitCode: number): DashboardStatus {
	if (exitCode === 0) {
		return 'PASS';
	}
	return 'FAIL';
}

function trimOutput(text: string): string {
	if (text.length <= OUTPUT_LIMIT) {
		return text;
	}
	return `${text.slice(0, OUTPUT_LIMIT)}\n...[truncated]`;
}

async function resolveOperatorRunDir(runDir?: string): Promise<string | null> {
	if (runDir && runDir.trim()) {
		return path.isAbsolute(runDir) ? runDir : repoJoin(runDir);
	}

	const obsRoot = repoJoin('.local/obs');
	const summaryFiles = await walkFiles(obsRoot, {
		maxDepth: 10,
		maxResults: 3000,
		match: (absPath) =>
			absPath.endsWith(`${path.sep}summary.json`) && absPath.includes('il_thread_runner_v2')
	});
	if (summaryFiles.length === 0) {
		return null;
	}

	let latestPath: string | null = null;
	let latestTime = 0;
	for (const absPath of summaryFiles) {
		try {
			const stat = await fs.stat(absPath);
			if (stat.mtimeMs > latestTime) {
				latestTime = stat.mtimeMs;
				latestPath = absPath;
			}
		} catch {
			continue;
		}
	}

	if (!latestPath) {
		return null;
	}
	return path.dirname(latestPath);
}

async function commandForPipeline(
	pipeline: PipelineKey,
	runDir?: string
): Promise<{ cmd: string[]; runDir: string | null }> {
	const py = pythonExecutable();
	switch (pipeline) {
		case 'rag':
			return { cmd: [py, 'scripts/ops/s25_rag_tuning_loop.py'], runDir: null };
		case 'langchain':
			return { cmd: [py, 'scripts/ops/s25_langchain_poc.py'], runDir: null };
		case 'ml':
			return { cmd: [py, 'scripts/ops/s25_ml_experiment.py'], runDir: null };
		case 'quality':
			return { cmd: [py, 'scripts/ops/s30_quality_burndown.py'], runDir: null };
		case 'operator': {
			const resolvedRunDir = await resolveOperatorRunDir(runDir);
			if (!resolvedRunDir) {
				throw new Error(
					'No il_thread_runner_v2 run directory found. Pass runDir explicitly.'
				);
			}
			return {
				cmd: [
					py,
					'scripts/ops/s32_operator_dashboard_export.py',
					'--run-dir',
					resolvedRunDir
				],
				runDir: resolvedRunDir
			};
		}
		default:
			throw new Error(`Unsupported pipeline: ${pipeline}`);
	}
}

async function runCommand(
	pipeline: PipelineKey,
	command: string[],
	runDir: string | null
): Promise<CommandRunResult> {
	const started = new Date();
	return await new Promise<CommandRunResult>((resolve) => {
		const child = spawn(command[0], command.slice(1), {
			cwd: REPO_ROOT,
			env: {
				...process.env,
				PYTHONPATH: './src:.'
			}
		});

		let stdout = '';
		let stderr = '';
		let killedByTimeout = false;

		const timer = setTimeout(() => {
			killedByTimeout = true;
			child.kill('SIGTERM');
		}, COMMAND_TIMEOUT_MS);

		child.stdout.on('data', (chunk: Buffer | string) => {
			stdout += chunk.toString();
		});
		child.stderr.on('data', (chunk: Buffer | string) => {
			stderr += chunk.toString();
		});

		child.on('error', (error: Error) => {
			clearTimeout(timer);
			const ended = new Date();
			resolve({
				pipeline,
				command,
				status: 'FAIL',
				exitCode: 1,
				startedAt: started.toISOString(),
				endedAt: ended.toISOString(),
				durationMs: ended.getTime() - started.getTime(),
				runDir,
				stdout: trimOutput(stdout),
				stderr: trimOutput(`${stderr}\n${error.message}`)
			});
		});

		child.on('close', (code: number | null) => {
			clearTimeout(timer);
			const ended = new Date();
			const effectiveCode = killedByTimeout ? 124 : (code ?? 1);
			const timeoutNote = killedByTimeout
				? '\n[timeout] command exceeded 20 minutes and was terminated.'
				: '';
			resolve({
				pipeline,
				command,
				status: toStatus(effectiveCode),
				exitCode: effectiveCode,
				startedAt: started.toISOString(),
				endedAt: ended.toISOString(),
				durationMs: ended.getTime() - started.getTime(),
				runDir,
				stdout: trimOutput(stdout),
				stderr: trimOutput(`${stderr}${timeoutNote}`)
			});
		});
	});
}

export async function runPipeline(
	pipeline: PipelineKey,
	runDir?: string
): Promise<CommandRunResult> {
	const command = await commandForPipeline(pipeline, runDir);
	return runCommand(pipeline, command.cmd, command.runDir);
}

export async function runAllPipelines(runDir?: string): Promise<PipelineRunResponse> {
	const order: PipelineKey[] = ['rag', 'langchain', 'ml', 'quality', 'operator'];
	const results: CommandRunResult[] = [];
	for (const pipeline of order) {
		const result = await runPipeline(pipeline, runDir);
		results.push(result);
	}
	const hasFail = results.some((row) => row.status === 'FAIL');
	const hasWarn = results.some((row) => row.status === 'WARN');
	return {
		status: hasFail ? 'FAIL' : hasWarn ? 'WARN' : 'PASS',
		results
	};
}

export async function runSinglePipeline(
	pipeline: PipelineKey,
	runDir?: string
): Promise<PipelineRunResponse> {
	const result = await runPipeline(pipeline, runDir);
	return {
		status: result.status,
		results: [result]
	};
}
