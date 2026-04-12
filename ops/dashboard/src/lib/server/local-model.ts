import { existsSync, readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

import { REPO_ROOT, asString, repoJoin } from './fs';
import {
	postOpenAiCompatChat,
	resolveOpenAiCompatApiBase,
	type OpenAiCompatChatRequest,
	type OpenAiCompatChatResponse
} from './openai-compat';

export type LocalModelBackend = 'openai_compat' | 'gemma_lab';

export interface LocalModelChatRequest {
	apiBase?: string | null;
	apiKey?: string | null;
	model?: string | null;
	temperature?: number;
	messages: OpenAiCompatChatRequest['messages'];
}

export interface LocalModelChatResponse {
	content: string;
	resolvedTarget: string;
	backend: LocalModelBackend;
	model: string;
}

interface GemmaLabBridgePayload {
	status?: unknown;
	model_id?: unknown;
	output_text?: unknown;
	cache_dir?: unknown;
	cache_exists?: unknown;
	root?: unknown;
	python?: unknown;
	error?: unknown;
}

export interface GemmaLabProbeResult {
	status: 'ok' | 'error';
	modelId: string;
	cacheDir: string;
	cacheExists: boolean;
	root: string;
	python: string;
	error: string;
}

const DEFAULT_OPENAI_MODEL = 'Qwen2.5-7B-Instruct';
const DEFAULT_GEMMA_MODEL = 'google/gemma-4-E2B-it';
const GEMMA_BRIDGE_TIMEOUT_MS = 20 * 60 * 1000;
let cachedDashboardEnv: Record<string, string> | null = null;

function trimOneLine(value: string, limit = 180): string {
	const text = value.replace(/\s+/g, ' ').trim();
	if (text.length <= limit) {
		return text;
	}
	return `${text.slice(0, limit).trimEnd()}...`;
}

function parseEnvFile(raw: string): Record<string, string> {
	const out: Record<string, string> = {};
	for (const line of raw.split(/\r?\n/)) {
		const trimmed = line.trim();
		if (!trimmed || trimmed.startsWith('#')) {
			continue;
		}
		const eq = trimmed.indexOf('=');
		if (eq <= 0) {
			continue;
		}
		const key = trimmed.slice(0, eq).trim();
		let value = trimmed.slice(eq + 1).trim();
		if (
			(value.startsWith('"') && value.endsWith('"')) ||
			(value.startsWith("'") && value.endsWith("'"))
		) {
			value = value.slice(1, -1);
		}
		if (key) {
			out[key] = value;
		}
	}
	return out;
}

function readDashboardEnv(): Record<string, string> {
	if (cachedDashboardEnv) {
		return cachedDashboardEnv;
	}
	const envPath = path.resolve(REPO_ROOT, 'ops/dashboard/.env');
	if (!existsSync(envPath)) {
		cachedDashboardEnv = {};
		return cachedDashboardEnv;
	}
	cachedDashboardEnv = parseEnvFile(readFileSync(envPath, 'utf-8'));
	return cachedDashboardEnv;
}

function envValue(name: string): string {
	const direct = asString(process.env[name]).trim();
	if (direct) {
		return direct;
	}
	return asString(readDashboardEnv()[name]).trim();
}

export function resolveLocalModelBackend(): LocalModelBackend {
	const raw = envValue('LOCAL_MODEL_BACKEND').toLowerCase();
	return raw === 'gemma_lab' ? 'gemma_lab' : 'openai_compat';
}

export function resolveOpenAiModelName(): string {
	return envValue('LOCAL_GGUF_MODEL') || DEFAULT_OPENAI_MODEL;
}

export function resolveGemmaModelId(): string {
	return envValue('GEMMA_MODEL_ID') || DEFAULT_GEMMA_MODEL;
}

export function resolveLocalModelName(): string {
	return resolveLocalModelBackend() === 'gemma_lab'
		? resolveGemmaModelId()
		: resolveOpenAiModelName();
}

export function resolveLocalModelRuntimeLabel(): string {
	return resolveLocalModelBackend() === 'gemma_lab'
		? 'gemma-lab direct'
		: resolveOpenAiCompatApiBase(envValue('OPENAI_API_BASE'));
}

export function resolveGemmaLabRoot(): string {
	const envRoot = envValue('GEMMA_LAB_ROOT');
	if (envRoot) {
		return path.resolve(envRoot);
	}
	return path.resolve(REPO_ROOT, '..', 'gemma-lab');
}

export function resolveGemmaLabPython(): string {
	const envPython = envValue('GEMMA_LAB_PYTHON');
	if (envPython) {
		return path.resolve(envPython);
	}
	return path.join(resolveGemmaLabRoot(), '.venv', 'bin', 'python');
}

function gemmaBridgePath(): string {
	return repoJoin('scripts/gemma_lab_bridge.py');
}

async function runGemmaLabBridge(
	mode: 'probe' | 'chat',
	payload?: Record<string, unknown>
): Promise<GemmaLabBridgePayload> {
	const gemmaRoot = resolveGemmaLabRoot();
	const python = resolveGemmaLabPython();
	const bridge = gemmaBridgePath();

	if (!existsSync(gemmaRoot)) {
		throw new Error(`gemma-lab root not found: ${gemmaRoot}`);
	}
	if (python.includes(path.sep) && !existsSync(python)) {
		throw new Error(`gemma-lab python not found: ${python}`);
	}
	if (!existsSync(bridge)) {
		throw new Error(`gemma bridge script not found: ${bridge}`);
	}

	const args = [bridge, '--mode', mode, '--gemma-root', gemmaRoot];
	const modelId = asString(payload?.model_id).trim();
	if (modelId) {
		args.push('--model-id', modelId);
	}

	return await new Promise<GemmaLabBridgePayload>((resolve, reject) => {
		const child = spawn(python, args, {
			cwd: REPO_ROOT,
			env: {
				...process.env,
				GEMMA_LAB_ROOT: gemmaRoot
			}
		});

		let stdout = '';
		let stderr = '';
		let timedOut = false;
		const timer = setTimeout(() => {
			timedOut = true;
			child.kill('SIGTERM');
		}, GEMMA_BRIDGE_TIMEOUT_MS);

		child.stdout.on('data', (chunk: Buffer | string) => {
			stdout += chunk.toString();
		});
		child.stderr.on('data', (chunk: Buffer | string) => {
			stderr += chunk.toString();
		});
		child.on('error', (error) => {
			clearTimeout(timer);
			reject(error);
		});
		child.on('close', (code: number | null) => {
			clearTimeout(timer);
			const text = stdout.trim();
			let parsed: GemmaLabBridgePayload = {};
			if (text) {
				try {
					const candidate = JSON.parse(text);
					if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
						parsed = candidate as GemmaLabBridgePayload;
					}
				} catch (error) {
					reject(
						new Error(
							`gemma bridge returned invalid JSON: ${trimOneLine(
								error instanceof Error ? error.message : String(error)
							)}`
						)
					);
					return;
				}
			}
			if (timedOut) {
				reject(new Error('gemma bridge timed out after 20 minutes'));
				return;
			}
			if ((code ?? 1) !== 0 && asString(parsed.error).trim() === '') {
				reject(
					new Error(
						trimOneLine(stderr || stdout || `gemma bridge exited with code ${code ?? 1}`)
					)
				);
				return;
			}
			resolve(parsed);
		});

		if (mode === 'chat') {
			child.stdin.write(JSON.stringify(payload || {}));
		}
		child.stdin.end();
	});
}

export async function probeGemmaLabRuntime(): Promise<GemmaLabProbeResult> {
	try {
		const payload = await runGemmaLabBridge('probe', {
			model_id: resolveGemmaModelId()
		});
		if (asString(payload.status).trim().toLowerCase() !== 'ok') {
			return {
				status: 'error',
				modelId: resolveGemmaModelId(),
				cacheDir: '',
				cacheExists: false,
				root: resolveGemmaLabRoot(),
				python: resolveGemmaLabPython(),
				error: asString(payload.error).trim() || 'gemma-lab probe failed'
			};
		}
		return {
			status: 'ok',
			modelId: asString(payload.model_id).trim() || resolveGemmaModelId(),
			cacheDir: asString(payload.cache_dir).trim(),
			cacheExists: Boolean(payload.cache_exists),
			root: asString(payload.root).trim() || resolveGemmaLabRoot(),
			python: asString(payload.python).trim() || resolveGemmaLabPython(),
			error: ''
		};
	} catch (error) {
		return {
			status: 'error',
			modelId: resolveGemmaModelId(),
			cacheDir: '',
			cacheExists: false,
			root: resolveGemmaLabRoot(),
			python: resolveGemmaLabPython(),
			error: error instanceof Error ? error.message : String(error)
		};
	}
}

export async function postLocalModelChat(
	request: LocalModelChatRequest
): Promise<LocalModelChatResponse> {
	if (resolveLocalModelBackend() === 'gemma_lab') {
		const model = asString(request.model).trim() || resolveGemmaModelId();
		const payload = await runGemmaLabBridge('chat', {
			model_id: model,
			messages: request.messages
		});
		if (asString(payload.status).trim().toLowerCase() !== 'ok') {
			throw new Error(asString(payload.error).trim() || 'gemma-lab chat failed');
		}
		const content = asString(payload.output_text).trim();
		if (!content) {
			throw new Error('gemma-lab returned empty content');
		}
		return {
			content,
			resolvedTarget: 'gemma-lab direct',
			backend: 'gemma_lab',
			model: asString(payload.model_id).trim() || model
		};
	}

	const apiBase = resolveOpenAiCompatApiBase(request.apiBase);
	const apiKey = asString(request.apiKey).trim() || process.env.OPENAI_API_KEY || 'dummy';
	const model = asString(request.model).trim() || resolveOpenAiModelName();
	const response: OpenAiCompatChatResponse = await postOpenAiCompatChat({
		apiBase,
		apiKey,
		model,
		temperature: request.temperature ?? 0,
		messages: request.messages
	});
	return {
		content: response.content,
		resolvedTarget: response.resolvedUrl,
		backend: 'openai_compat',
		model
	};
}
