import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import { promises as fs } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

import {
	REPO_ROOT,
	asNumber,
	asString,
	normalizeStatus,
	readJsonObject,
	repoJoin,
	toRepoRelative,
	walkFiles
} from './fs';
import {
	resolveGemmaLabPython,
	resolveGemmaLabRoot,
	resolveLocalModelBackend,
	resolveLocalModelName,
	resolveLocalModelRuntimeLabel
} from './local-model';
import {
	extractReferenceRetrievals,
	recordRunInspector,
	summarizeFailureReason,
	type RunInspectorMessageInput,
	type RunInspectorRetrievalInput
} from './run-inspector-data';
import type {
	AiLabChannel,
	AiLabRunRecord,
	AiLabRunRequest,
	AiLabRunResponse,
	DashboardStatus,
	FineTuneHistoryItem
} from './types';

const HISTORY_FILE = repoJoin('.local/obs/dashboard/ai_lab_runs.jsonl');
const COMMAND_TIMEOUT_MS = 20 * 60 * 1000;
const OUTPUT_LIMIT = 120_000;

function pythonExecutable(): string {
	const venvPython = repoJoin('.venv/bin/python');
	if (existsSync(venvPython)) {
		return venvPython;
	}
	return 'python3';
}

function trimOutput(text: string): string {
	if (text.length <= OUTPUT_LIMIT) {
		return text;
	}
	return `${text.slice(0, OUTPUT_LIMIT)}\n...[truncated]`;
}

function statusFromExitCode(exitCode: number): DashboardStatus {
	if (exitCode === 0) {
		return 'PASS';
	}
	return 'FAIL';
}

function shellEscape(value: string): string {
	return `'${value.replaceAll("'", "'\\''")}'`;
}

async function appendJsonlRecord(absPath: string, row: Record<string, unknown>): Promise<void> {
	const dir = path.dirname(absPath);
	await fs.mkdir(dir, { recursive: true });
	await fs.appendFile(absPath, `${JSON.stringify(row, null, 0)}\n`, 'utf-8');
}

async function runProcess(args: {
	command: string[];
	shellCommand?: string;
	channel: AiLabChannel;
	prompt: string;
	artifactPath: string | null;
	envOverrides?: Record<string, string>;
	model?: string;
	apiBase?: string;
	messages?: RunInspectorMessageInput[];
	retrievals?: RunInspectorRetrievalInput[];
	metadata?: Record<string, unknown>;
}): Promise<AiLabRunResponse> {
	const started = new Date();

	const execution = await new Promise<{
		exitCode: number;
		stdout: string;
		stderr: string;
	}>((resolve) => {
		const child = args.shellCommand
			? spawn('zsh', ['-lc', args.shellCommand], {
					cwd: REPO_ROOT,
					env: {
						...process.env,
						...(args.envOverrides || {}),
						PYTHONPATH: './src:.'
					}
				})
			: spawn(args.command[0], args.command.slice(1), {
					cwd: REPO_ROOT,
					env: {
						...process.env,
						...(args.envOverrides || {}),
						PYTHONPATH: './src:.'
					}
				});

		let stdout = '';
		let stderr = '';
		let timedOut = false;

		const timer = setTimeout(() => {
			timedOut = true;
			child.kill('SIGTERM');
		}, COMMAND_TIMEOUT_MS);

		child.stdout.on('data', (chunk: Buffer | string) => {
			stdout += chunk.toString();
		});
		child.stderr.on('data', (chunk: Buffer | string) => {
			stderr += chunk.toString();
		});

		child.on('error', (error) => {
			clearTimeout(timer);
			resolve({
				exitCode: 1,
				stdout,
				stderr: `${stderr}\n${error.message}`
			});
		});

		child.on('close', (code: number | null) => {
			clearTimeout(timer);
			const exitCode = timedOut ? 124 : (code ?? 1);
			const timeoutMessage = timedOut
				? '\n[timeout] command exceeded 20 minutes and was terminated.'
				: '';
			resolve({
				exitCode,
				stdout,
				stderr: `${stderr}${timeoutMessage}`
			});
		});
	});

	const ended = new Date();
	const record: AiLabRunRecord = {
		id: randomUUID(),
		channel: args.channel,
		createdAt: ended.toISOString(),
		prompt: args.prompt,
		command: args.shellCommand || args.command.join(' '),
		status: statusFromExitCode(execution.exitCode),
		exitCode: execution.exitCode,
		durationMs: ended.getTime() - started.getTime(),
		artifactPath: args.artifactPath,
		stdout: trimOutput(execution.stdout),
		stderr: trimOutput(execution.stderr)
	};

	await appendJsonlRecord(HISTORY_FILE, record as unknown as Record<string, unknown>);
	const defaultRetrievals =
		args.channel === 'local-model' ? extractReferenceRetrievals(record.stdout) : [];
	const outputText = record.stdout || record.stderr;
	const errorReason =
		record.status === 'FAIL'
			? summarizeFailureReason(record.stderr, record.stdout) ||
				(record.exitCode !== 0 ? `exit_code=${record.exitCode}` : '')
			: '';
	let inspector: AiLabRunResponse['inspector'];
	try {
		inspector = await recordRunInspector({
			id: record.id,
			scope: 'ai-lab',
			source: record.channel,
			status: record.status,
			createdAt: record.createdAt,
			prompt: record.prompt,
			outputText,
			command: record.command,
			model: asString(args.model).trim(),
			apiBase: asString(args.apiBase).trim(),
			durationMs: record.durationMs,
			errorReason,
			metadata: {
				channel: record.channel,
				exitCode: record.exitCode,
				artifactPath: record.artifactPath,
				...(args.metadata || {})
			},
			messages: args.messages || [
				{ seq: 0, role: 'user', content: record.prompt },
				{ seq: 1, role: 'assistant', content: outputText }
			],
			retrievals: args.retrievals || defaultRetrievals
		});
	} catch {
		inspector = undefined;
	}
	return {
		status: record.status,
		record,
		inspector
	};
}

async function resolveLatestFineTuneReportPath(): Promise<string | null> {
	const root = repoJoin('.local/obs');
	const reports = await walkFiles(root, {
		maxDepth: 4,
		maxResults: 2000,
		match: (absPath) => absPath.endsWith('il.compile.prompt_loop.json')
	});

	let latestPath: string | null = null;
	let latestMtime = 0;
	for (const absPath of reports) {
		try {
			const stat = await fs.stat(absPath);
			if (stat.mtimeMs > latestMtime) {
				latestMtime = stat.mtimeMs;
				latestPath = absPath;
			}
		} catch {
			continue;
		}
	}
	return latestPath ? toRepoRelative(latestPath) : null;
}

function buildCommandFromTemplate(template: string, prompt: string): string {
	const source = template.trim();
	if (!source) {
		throw new Error('commandTemplate is required for MCP/AI CLI channels.');
	}
	if (source.includes('{prompt}')) {
		return source.replaceAll('{prompt}', shellEscape(prompt));
	}
	return `${source} ${shellEscape(prompt)}`;
}

export async function runAiLab(request: AiLabRunRequest): Promise<AiLabRunResponse> {
	const channel = request.channel;
	const prompt = asString(request.prompt).trim();
	const py = pythonExecutable();

	switch (channel) {
		case 'local-model': {
			if (!prompt) {
				throw new Error('prompt is required for local-model channel.');
			}
			const requestedModel = asString(request.model).trim();
			const model = requestedModel || resolveLocalModelName();
			const apiBase = resolveLocalModelRuntimeLabel();
			const backend = resolveLocalModelBackend();
			const envOverrides: Record<string, string> =
				backend === 'gemma_lab'
					? {
							LOCAL_MODEL_BACKEND: 'gemma_lab',
							GEMMA_MODEL_ID: model,
							GEMMA_LAB_ROOT: resolveGemmaLabRoot(),
							GEMMA_LAB_PYTHON: resolveGemmaLabPython(),
							LOCAL_GGUF_MODEL: model
						}
					: {
							LOCAL_MODEL_BACKEND: 'openai_compat',
							LOCAL_GGUF_MODEL: model,
							OPENAI_API_BASE: apiBase
						};
			return runProcess({
				command: [py, 'src/ask.py', prompt],
				channel,
				prompt,
				artifactPath: null,
				envOverrides,
				model,
				apiBase
			});
		}
		case 'fine-tune': {
			const command = [py, 'scripts/il_compile_prompt_loop.py'];
			const profiles = asString(request.profiles).trim();
			if (profiles) {
				command.push('--profiles', profiles);
			}
			const seed = asNumber(request.seed);
			if (seed !== null) {
				command.push('--seed', String(Math.trunc(seed)));
			}
			const response = await runProcess({
				command,
				channel,
				prompt: prompt || '(fine-tune prompt loop)',
				artifactPath: null,
				metadata: {
					profiles,
					seed: asNumber(request.seed)
				}
			});
			const latestReport = await resolveLatestFineTuneReportPath();
			return {
				...response,
				record: {
					...response.record,
					artifactPath: latestReport
				},
				inspector: response.inspector
					? {
							...response.inspector,
							metadata: {
								...response.inspector.metadata,
								artifactPath: latestReport
							}
						}
					: response.inspector
			};
		}
		case 'rag-tuning': {
			return runProcess({
				command: [py, 'scripts/ops/s25_rag_tuning_loop.py'],
				channel,
				prompt: prompt || '(rag tuning run)',
				artifactPath: 'docs/evidence/s25-08/rag_tuning_latest.json',
				metadata: {
					pipeline: 'rag'
				}
			});
		}
		case 'langchain': {
			return runProcess({
				command: [py, 'scripts/ops/s25_langchain_poc.py'],
				channel,
				prompt: prompt || '(langchain run)',
				artifactPath: 'docs/evidence/s25-09/langchain_poc_latest.json',
				metadata: {
					pipeline: 'langchain'
				}
			});
		}
		case 'mcp':
		case 'ai-cli': {
			const shellCommand = buildCommandFromTemplate(
				asString(request.commandTemplate),
				prompt
			);
			return runProcess({
				command: [],
				shellCommand,
				channel,
				prompt,
				artifactPath: null,
				metadata: {
					template: asString(request.commandTemplate).trim()
				}
			});
		}
		default:
			throw new Error(`Unsupported channel: ${channel}`);
	}
}

export async function getAiLabHistory(limit = 60): Promise<AiLabRunRecord[]> {
	if (!existsSync(HISTORY_FILE)) {
		return [];
	}

	const raw = await fs.readFile(HISTORY_FILE, 'utf-8');
	const items: AiLabRunRecord[] = [];
	for (const line of raw.split(/\r?\n/)) {
		const text = line.trim();
		if (!text) {
			continue;
		}
		try {
			const obj = JSON.parse(text) as Record<string, unknown>;
			items.push({
				id: asString(obj.id) || randomUUID(),
				channel: asString(obj.channel) as AiLabChannel,
				createdAt: asString(obj.createdAt) || new Date(0).toISOString(),
				prompt: asString(obj.prompt),
				command: asString(obj.command),
				status: normalizeStatus(obj.status),
				exitCode: asNumber(obj.exitCode) ?? 1,
				durationMs: asNumber(obj.durationMs) ?? 0,
				artifactPath: asString(obj.artifactPath) || null,
				stdout: asString(obj.stdout),
				stderr: asString(obj.stderr)
			});
		} catch {
			continue;
		}
	}

	items.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
	return items.slice(0, Math.max(1, limit));
}

export async function getFineTuneHistory(limit = 30): Promise<FineTuneHistoryItem[]> {
	const root = repoJoin('.local/obs');
	const reports = await walkFiles(root, {
		maxDepth: 4,
		maxResults: 2000,
		match: (absPath) => absPath.endsWith('il.compile.prompt_loop.json')
	});

	const rows: FineTuneHistoryItem[] = [];
	for (const absPath of reports) {
		const payload = await readJsonObject(absPath);
		if (!payload) {
			continue;
		}
		let stat;
		try {
			stat = await fs.stat(absPath);
		} catch {
			continue;
		}
		const best = (payload.best || {}) as Record<string, unknown>;
		const fallbackCount = asNumber(best.fallback_count);
		const objectiveScore = asNumber(best.objective_score);
		rows.push({
			id: `${toRepoRelative(absPath)}:${stat.mtimeMs}`,
			capturedAt: stat.mtime.toISOString(),
			reportPath: toRepoRelative(absPath),
			model: asString(payload.model) || 'unknown',
			bestProfile: asString(best.profile) || 'unknown',
			fallbackCount,
			objectiveScore,
			status: fallbackCount === null || objectiveScore === null ? 'WARN' : 'PASS'
		});
	}

	rows.sort((a, b) => new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime());
	return rows.slice(0, Math.max(1, limit));
}
