import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import { promises as fs } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

import { asString, normalizeStatus, repoJoin } from './fs';
import { buildConsensusText, evaluateContract, evidenceRefsFromText } from './consensus-logic';
import { postOpenAiCompatChat, resolveOpenAiCompatApiBase } from './openai-compat';
import type {
	ConsensusAgentResult,
	ConsensusRecord,
	ConsensusRunRequest,
	ConsensusRunResponse,
	DashboardStatus
} from './types';

const HISTORY_FILE = repoJoin('.local/obs/dashboard/consensus_runs.jsonl');
const CONTRACT_VIOLATION_DIR = repoJoin('docs/evidence/dashboard/consensus_contract');
const CONTRACT_VIOLATION_LATEST_FILE = repoJoin(
	'docs/evidence/dashboard/consensus_contract_latest.json'
);
const OUTPUT_LIMIT = 120_000;
const COMMAND_TIMEOUT_MS = 20 * 60 * 1000;

interface ConsensusContractViolationEvidence {
	schema_version: 'consensus_contract.v1';
	captured_at_utc: string;
	status: DashboardStatus;
	summary: {
		status: DashboardStatus;
		errors: string[];
		contract: {
			minAgents: number;
			requiredEvidence: boolean;
			requiredGuards: boolean;
		};
		passAgents: number;
		activeAgents: number;
		evidenceRefCount: number;
	};
	record_id: string;
	run_path: string;
	prompt_preview: string;
	timeline_ms: {
		total: number;
		local: number | null;
		cli: number | null;
		api: number | null;
	};
	agents: Array<{
		agent: ConsensusAgentResult['agent'];
		status: DashboardStatus;
		duration_ms: number;
		guard_passed: boolean;
		evidence_ref_count: number;
	}>;
}

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

function shellEscape(value: string): string {
	return `'${value.replaceAll("'", "'\\''")}'`;
}

async function appendJsonl(absPath: string, row: Record<string, unknown>): Promise<void> {
	await fs.mkdir(path.dirname(absPath), { recursive: true });
	await fs.appendFile(absPath, `${JSON.stringify(row)}\n`, 'utf-8');
}

function compactPrompt(text: string): string {
	const clean = text.replace(/\s+/g, ' ').trim();
	if (clean.length <= 240) {
		return clean;
	}
	return `${clean.slice(0, 240)}...`;
}

function toTimestampSlug(isoUtc: string): string {
	return isoUtc.replace(/[-:.]/g, '').replace('T', '_').replace('Z', 'Z');
}

function buildContractViolationEvidence(
	record: ConsensusRecord,
	runPath: string
): ConsensusContractViolationEvidence {
	const passAgents = record.agents.filter((item) => item.status === 'PASS').length;
	const activeAgents = record.agents.filter((item) => item.status !== 'SKIP').length;
	return {
		schema_version: 'consensus_contract.v1',
		captured_at_utc: record.createdAt,
		status: record.result.status,
		summary: {
			status: record.result.status,
			errors: record.guard.details,
			contract: record.contract,
			passAgents,
			activeAgents,
			evidenceRefCount: record.evidence.refs.length
		},
		record_id: record.id,
		run_path: runPath,
		prompt_preview: compactPrompt(record.prompt),
		timeline_ms: {
			total: record.timeline.totalMs,
			local: record.timeline.localMs,
			cli: record.timeline.cliMs,
			api: record.timeline.apiMs
		},
		agents: record.agents.map((item) => ({
			agent: item.agent,
			status: item.status,
			duration_ms: item.durationMs,
			guard_passed: item.guardPassed,
			evidence_ref_count: item.evidenceRefs.length
		}))
	};
}

async function writeContractViolationEvidence(record: ConsensusRecord): Promise<void> {
	if (record.result.status === 'PASS') {
		return;
	}
	const stamp = toTimestampSlug(record.createdAt);
	const fileName = `consensus_contract_${stamp}_${record.id.slice(0, 8)}.json`;
	const runPath = path.join(CONTRACT_VIOLATION_DIR, fileName);
	const relativeRunPath = path.relative(repoJoin(), runPath).replaceAll(path.sep, '/');
	const payload = buildContractViolationEvidence(record, relativeRunPath);

	await fs.mkdir(CONTRACT_VIOLATION_DIR, { recursive: true });
	await fs.writeFile(runPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf-8');
	await fs.writeFile(
		CONTRACT_VIOLATION_LATEST_FILE,
		`${JSON.stringify(payload, null, 2)}\n`,
		'utf-8'
	);
}

async function runCommand(args: {
	agent: 'local' | 'cli';
	command: string[];
	shellCommand?: string;
}): Promise<{ exitCode: number; stdout: string; stderr: string; durationMs: number }> {
	const started = Date.now();
	return await new Promise((resolve) => {
		const child = args.shellCommand
			? spawn('zsh', ['-lc', args.shellCommand], {
					cwd: repoJoin(),
					env: { ...process.env, PYTHONPATH: './src:.' }
				})
			: spawn(args.command[0], args.command.slice(1), {
					cwd: repoJoin(),
					env: { ...process.env, PYTHONPATH: './src:.' }
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
				stderr: `${stderr}\n${error.message}`,
				durationMs: Date.now() - started
			});
		});
		child.on('close', (code: number | null) => {
			clearTimeout(timer);
			const exitCode = timedOut ? 124 : (code ?? 1);
			const timeoutText = timedOut
				? '\n[timeout] command exceeded 20 minutes and was terminated.'
				: '';
			resolve({
				exitCode,
				stdout,
				stderr: `${stderr}${timeoutText}`,
				durationMs: Date.now() - started
			});
		});
	});
}

async function runLocalAgent(prompt: string): Promise<ConsensusAgentResult> {
	if (!prompt.trim()) {
		return {
			agent: 'local',
			status: 'SKIP',
			durationMs: 0,
			command: 'skipped (empty prompt)',
			output: '',
			error: 'prompt is empty',
			evidenceRefs: [],
			guardPassed: false
		};
	}
	const py = pythonExecutable();
	const command = [py, 'src/ask.py', prompt];
	const result = await runCommand({ agent: 'local', command });
	const status: DashboardStatus = result.exitCode === 0 ? 'PASS' : 'FAIL';
	const output = trimOutput(result.stdout);
	const error = trimOutput(result.stderr);
	const evidenceRefs = evidenceRefsFromText(output);
	return {
		agent: 'local',
		status,
		durationMs: result.durationMs,
		command: command.join(' '),
		output,
		error,
		evidenceRefs,
		guardPassed: status === 'PASS' && output.trim().length > 0
	};
}

async function runCliAgent(prompt: string, template: string): Promise<ConsensusAgentResult> {
	if (!template.trim()) {
		return {
			agent: 'cli',
			status: 'SKIP',
			durationMs: 0,
			command: 'skipped (template not provided)',
			output: '',
			error: 'cliCommandTemplate is empty',
			evidenceRefs: [],
			guardPassed: false
		};
	}
	const shellCommand = template.includes('{prompt}')
		? template.replaceAll('{prompt}', shellEscape(prompt))
		: `${template} ${shellEscape(prompt)}`;
	const result = await runCommand({ agent: 'cli', command: [], shellCommand });
	const status: DashboardStatus = result.exitCode === 0 ? 'PASS' : 'FAIL';
	const output = trimOutput(result.stdout);
	const error = trimOutput(result.stderr);
	const evidenceRefs = evidenceRefsFromText(output);
	return {
		agent: 'cli',
		status,
		durationMs: result.durationMs,
		command: shellCommand,
		output,
		error,
		evidenceRefs,
		guardPassed: status === 'PASS' && output.trim().length > 0
	};
}

async function runApiAgent(request: ConsensusRunRequest): Promise<ConsensusAgentResult> {
	const apiBase = resolveOpenAiCompatApiBase(asString(request.apiBase).trim());
	const apiModel = asString(request.apiModel).trim();
	const prompt = asString(request.prompt);
	if (!asString(request.apiBase).trim() || !apiModel) {
		return {
			agent: 'api',
			status: 'SKIP',
			durationMs: 0,
			command: 'skipped (apiBase/apiModel not provided)',
			output: '',
			error: 'apiBase and apiModel are required for api agent',
			evidenceRefs: [],
			guardPassed: false
		};
	}

	const started = Date.now();
	const apiKey = asString(request.apiKey).trim() || process.env.OPENAI_API_KEY || 'dummy';
	try {
		const response = await postOpenAiCompatChat({
			apiBase,
			apiKey,
			model: apiModel,
			temperature: 0,
			messages: [
				{ role: 'system', content: 'Answer briefly with evidence and uncertainty.' },
				{ role: 'user', content: prompt }
			]
		});
		const durationMs = Date.now() - started;
		const content = response.content;
		const evidenceRefs = evidenceRefsFromText(content);
		return {
			agent: 'api',
			status: 'PASS',
			durationMs,
			command: `POST ${response.resolvedUrl}`,
			output: trimOutput(content),
			error: '',
			evidenceRefs,
			guardPassed: content.trim().length > 0
		};
	} catch (error) {
		const message = error instanceof Error ? error.message : 'api agent failed';
		return {
			agent: 'api',
			status: 'FAIL',
			durationMs: Date.now() - started,
			command: `POST ${apiBase}`,
			output: '',
			error: message,
			evidenceRefs: [],
			guardPassed: false
		};
	}
}

function finalizeRecord(
	prompt: string,
	agents: ConsensusAgentResult[],
	startedAt: number
): ConsensusRecord {
	const passAgents = agents.filter((a) => a.status === 'PASS');
	const activeAgents = agents.filter((a) => a.status !== 'SKIP');
	const allEvidence = [...new Set(agents.flatMap((a) => a.evidenceRefs))].slice(0, 50);

	const guardDetails: string[] = [];
	for (const item of activeAgents) {
		if (!item.guardPassed) {
			guardDetails.push(`${item.agent}: guard failed (empty output or execution failure)`);
		}
	}
	const evaluated = evaluateContract({
		passAgents: passAgents.length,
		activeAgents: activeAgents.length,
		evidenceCount: allEvidence.length,
		guardDetails
	});

	const local = agents.find((a) => a.agent === 'local');
	const cli = agents.find((a) => a.agent === 'cli');
	const api = agents.find((a) => a.agent === 'api');

	return {
		id: randomUUID(),
		createdAt: new Date().toISOString(),
		prompt,
		contract: evaluated.contract,
		guard: {
			passed: evaluated.details.length === 0,
			details: evaluated.details
		},
		evidence: {
			refs: allEvidence
		},
		result: {
			status: evaluated.status,
			summary: evaluated.summary,
			consensusText: buildConsensusText(agents)
		},
		timeline: {
			totalMs: Date.now() - startedAt,
			localMs: local ? local.durationMs : null,
			cliMs: cli ? cli.durationMs : null,
			apiMs: api ? api.durationMs : null
		},
		agents
	};
}

export async function runConsensus(request: ConsensusRunRequest): Promise<ConsensusRunResponse> {
	const prompt = asString(request.prompt).trim();
	if (!prompt) {
		throw new Error('prompt is required');
	}

	const startedAt = Date.now();
	const [local, cli, api] = await Promise.all([
		runLocalAgent(prompt),
		runCliAgent(prompt, asString(request.cliCommandTemplate)),
		runApiAgent(request)
	]);

	const record = finalizeRecord(prompt, [local, cli, api], startedAt);
	await appendJsonl(HISTORY_FILE, record as unknown as Record<string, unknown>);
	await writeContractViolationEvidence(record);
	return {
		status: record.result.status,
		record
	};
}

export async function getConsensusHistory(limit = 30): Promise<ConsensusRecord[]> {
	if (!existsSync(HISTORY_FILE)) {
		return [];
	}
	const raw = await fs.readFile(HISTORY_FILE, 'utf-8');
	const rows: ConsensusRecord[] = [];
	for (const line of raw.split(/\r?\n/)) {
		const text = line.trim();
		if (!text) {
			continue;
		}
		try {
			const obj = JSON.parse(text) as ConsensusRecord;
			rows.push({
				...obj,
				result: {
					...obj.result,
					status: normalizeStatus(obj.result?.status)
				}
			});
		} catch {
			continue;
		}
	}
	rows.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
	return rows.slice(0, Math.max(1, limit));
}
