import { existsSync } from 'node:fs';
import { promises as fs } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

import { REPO_ROOT, repoJoin, toRepoRelative } from './fs';
import { resolveOpenAiCompatApiBase } from './openai-compat';
import {
	probeGemmaLabRuntime,
	resolveLocalModelBackend,
	resolveLocalModelName,
	resolveLocalModelRuntimeLabel
} from './local-model';

export type RagGuideStatus = 'PASS' | 'WARN' | 'FAIL';

export interface RagLabGuideCheck {
	id: 'llm' | 'data' | 'index';
	status: RagGuideStatus;
	detail: string;
	hint: string;
}

export interface RagLabGuidePayload {
	apiBase: string;
	model: string;
	checks: RagLabGuideCheck[];
	dataRawPath: string;
	dataRawFileCount: number;
	indexDbPath: string;
	indexDbExists: boolean;
	indexDbSizeBytes: number;
	sampleNoteExists: boolean;
	readyToAsk: boolean;
}

export interface RagReadonlyFileEntry {
	path: string;
	sizeBytes: number;
	modifiedAt: string;
	preview: string;
}

export interface RagReadonlySnapshotPayload {
	generatedAt: string;
	dataRoot: string;
	totalFiles: number;
	files: RagReadonlyFileEntry[];
	indexDbPath: string;
	indexDbExists: boolean;
	indexDbSizeBytes: number;
}

export interface RagModelListPayload {
	apiBase: string;
	selectedModel: string;
	models: string[];
	resolvedEndpoint: string | null;
	error: string | null;
}

export interface RagDataWriteRequest {
	fileName: string;
	content: string;
	rebuildIndex?: boolean;
}

export interface RagDataWriteResponse {
	status: 'PASS' | 'FAIL';
	savedPath: string;
	savedBytes: number;
	rebuild: {
		ran: boolean;
		status: 'PASS' | 'FAIL';
		log: string;
	};
	snapshot: RagReadonlySnapshotPayload;
}

const TEXT_PREVIEW_EXTENSIONS = new Set([
	'.md',
	'.txt',
	'.json',
	'.jsonl',
	'.yaml',
	'.yml',
	'.toml',
	'.csv',
	'.tsv',
	'.log'
]);

function normalizeBaseRoot(apiBase: string): string {
	let base = (apiBase || '').trim().replace(/\/+$/, '');
	if (!base) {
		return 'http://127.0.0.1:11434';
	}
	if (base.endsWith('/chat/completions')) {
		base = base.slice(0, -'/chat/completions'.length).replace(/\/+$/, '');
	}
	if (base.endsWith('/v1')) {
		base = base.slice(0, -'/v1'.length).replace(/\/+$/, '');
	}
	return base || 'http://127.0.0.1:11434';
}

function dedupeKeepOrder(items: string[]): string[] {
	const out: string[] = [];
	for (const item of items) {
		if (item && !out.includes(item)) {
			out.push(item);
		}
	}
	return out;
}

function modelCheckUrls(apiBase: string): string[] {
	const root = normalizeBaseRoot(apiBase);
	return dedupeKeepOrder([`${root}/v1/models`, `${root}/models`]);
}

function healthCheckUrl(apiBase: string): string {
	return `${normalizeBaseRoot(apiBase)}/health`;
}

async function fetchTextWithTimeout(
	url: string,
	timeoutMs = 1800
): Promise<{ ok: boolean; status: number; text: string }> {
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);
	try {
		const response = await fetch(url, {
			method: 'GET',
			signal: controller.signal
		});
		const text = await response.text();
		return {
			ok: response.ok,
			status: response.status,
			text
		};
	} catch (error) {
		const detail = error instanceof Error ? error.message : String(error);
		return {
			ok: false,
			status: 0,
			text: detail
		};
	} finally {
		clearTimeout(timer);
	}
}

function modelCountFromBody(raw: string): number {
	if (!raw.trim()) {
		return 0;
	}
	try {
		const parsed = JSON.parse(raw) as {
			models?: unknown[];
			data?: unknown[];
		};
		if (Array.isArray(parsed.models)) {
			return parsed.models.length;
		}
		if (Array.isArray(parsed.data)) {
			return parsed.data.length;
		}
	} catch {
		// no-op
	}
	return 0;
}

function modelNamesFromBody(raw: string): string[] {
	if (!raw.trim()) {
		return [];
	}
	try {
		const parsed = JSON.parse(raw) as {
			models?: Array<{ id?: unknown; name?: unknown; model?: unknown }>;
			data?: Array<{ id?: unknown; name?: unknown; model?: unknown }>;
		};
		const rows = Array.isArray(parsed.models)
			? parsed.models
			: Array.isArray(parsed.data)
				? parsed.data
				: [];
		const out: string[] = [];
		for (const row of rows) {
			const candidate = [row.id, row.name, row.model]
				.map((value) => (typeof value === 'string' ? value.trim() : ''))
				.find((value) => value.length > 0);
			if (candidate && !out.includes(candidate)) {
				out.push(candidate);
			}
		}
		return out;
	} catch {
		return [];
	}
}

function shortOneLine(text: string, limit = 150): string {
	const oneLine = text.replace(/\s+/g, ' ').trim();
	if (oneLine.length <= limit) {
		return oneLine;
	}
	return `${oneLine.slice(0, limit).trimEnd()}...`;
}

function trimCommandLog(text: string, limit = 120_000): string {
	const source = text || '';
	if (source.length <= limit) {
		return source;
	}
	return `${source.slice(0, limit)}\n...[truncated]`;
}

function pythonExecutable(): string {
	const venvPython = repoJoin('.venv/bin/python');
	if (existsSync(venvPython)) {
		return venvPython;
	}
	return 'python3';
}

function sanitizeFileName(input: string): string {
	let name = (input || '').trim();
	name = name.replaceAll('\\', '/');
	if (name.includes('/')) {
		throw new Error('fileName must not include path separators.');
	}
	if (!/^[A-Za-z0-9._-]+$/.test(name)) {
		throw new Error('fileName can only use letters, numbers, dot, underscore, hyphen.');
	}
	if (!name.includes('.')) {
		name = `${name}.md`;
	}
	if (!name.toLowerCase().endsWith('.md')) {
		throw new Error('Only .md fileName is allowed in this UI.');
	}
	return name;
}

async function runBuildIndex(): Promise<{
	status: 'PASS' | 'FAIL';
	log: string;
}> {
	const py = pythonExecutable();
	const result = await new Promise<{
		exitCode: number;
		stdout: string;
		stderr: string;
	}>((resolve) => {
		const child = spawn(py, ['src/build_index.py'], {
			cwd: REPO_ROOT,
			env: {
				...process.env,
				PYTHONPATH: './src:.'
			}
		});
		let stdout = '';
		let stderr = '';
		child.stdout.on('data', (chunk: Buffer | string) => {
			stdout += chunk.toString();
		});
		child.stderr.on('data', (chunk: Buffer | string) => {
			stderr += chunk.toString();
		});
		child.on('error', (error) => {
			resolve({
				exitCode: 1,
				stdout,
				stderr: `${stderr}\n${error.message}`
			});
		});
		child.on('close', (code: number | null) => {
			resolve({
				exitCode: code ?? 1,
				stdout,
				stderr
			});
		});
	});

	const merged = [result.stdout, result.stderr].filter(Boolean).join('\n').trim();
	return {
		status: result.exitCode === 0 ? 'PASS' : 'FAIL',
		log: trimCommandLog(merged || '[no output]')
	};
}

async function checkLlm(apiBase: string): Promise<RagLabGuideCheck> {
	if (resolveLocalModelBackend() === 'gemma_lab') {
		const probe = await probeGemmaLabRuntime();
		if (probe.status === 'ok' && probe.cacheExists) {
			return {
				id: 'llm',
				status: 'PASS',
				detail: `Gemma Lab runtime ready (${probe.modelId})`,
				hint: 'Gemma runtime is ready. Next: check data/index and ask a sample question.'
			};
		}
		if (probe.status === 'ok') {
			return {
				id: 'llm',
				status: 'WARN',
				detail: `Gemma Lab runtime found (${probe.modelId}), but cache was not found at ${probe.cacheDir}`,
				hint: 'Ensure the model is cached locally or that Hugging Face access is available for the first run.'
			};
		}
		return {
			id: 'llm',
			status: 'FAIL',
			detail: `Gemma Lab runtime unavailable (${shortOneLine(probe.error || 'probe failed')})`,
			hint: 'Check GEMMA_LAB_ROOT / GEMMA_LAB_PYTHON and the gemma-lab virtualenv.'
		};
	}

	const attempts: string[] = [];
	for (const url of modelCheckUrls(apiBase)) {
		const response = await fetchTextWithTimeout(url);
		if (response.ok) {
			const models = modelCountFromBody(response.text);
			if (models > 0) {
				return {
					id: 'llm',
					status: 'PASS',
					detail: `OpenAI-compatible endpoint reachable (${url}), models=${models}`,
					hint: 'LLM is ready. Next: check data/index and ask a sample question.'
				};
			}
			return {
				id: 'llm',
				status: 'WARN',
				detail: `Endpoint reachable (${url}) but model list was empty`,
				hint: 'Verify model loading on llama-server logs.'
			};
		}
		const desc =
			response.status > 0
				? `${url} -> ${response.status}`
				: `${url} -> ${shortOneLine(response.text)}`;
		attempts.push(desc);
	}

	const health = await fetchTextWithTimeout(healthCheckUrl(apiBase));
	if (health.ok) {
		return {
			id: 'llm',
			status: 'FAIL',
			detail: 'Health endpoint responded, but /models endpoint was unavailable. This may be a non-LLM service.',
			hint: 'Check OPENAI_API_BASE. Example: http://127.0.0.1:11434/v1'
		};
	}

	return {
		id: 'llm',
		status: 'FAIL',
		detail: `LLM endpoint not reachable (${attempts.join(' | ') || 'no attempts'})`,
		hint: 'Start llama-server and verify OPENAI_API_BASE.'
	};
}

async function countFiles(rootDir: string, maxDepth = 3): Promise<number> {
	const stack: Array<{ dir: string; depth: number }> = [{ dir: rootDir, depth: 0 }];
	let count = 0;
	while (stack.length > 0) {
		const current = stack.pop();
		if (!current) {
			continue;
		}
		let entries;
		try {
			entries = await fs.readdir(current.dir, { withFileTypes: true });
		} catch {
			continue;
		}
		for (const entry of entries) {
			const abs = path.join(current.dir, entry.name);
			if (entry.isFile()) {
				count += 1;
				continue;
			}
			if (entry.isDirectory() && current.depth < maxDepth) {
				stack.push({ dir: abs, depth: current.depth + 1 });
			}
		}
	}
	return count;
}

async function listFiles(rootDir: string, maxDepth = 4): Promise<string[]> {
	const stack: Array<{ dir: string; depth: number }> = [{ dir: rootDir, depth: 0 }];
	const out: string[] = [];

	while (stack.length > 0) {
		const current = stack.pop();
		if (!current) {
			continue;
		}
		let entries;
		try {
			entries = await fs.readdir(current.dir, { withFileTypes: true });
		} catch {
			continue;
		}
		for (const entry of entries) {
			const abs = path.join(current.dir, entry.name);
			if (entry.isFile()) {
				out.push(abs);
				continue;
			}
			if (entry.isDirectory() && current.depth < maxDepth) {
				stack.push({ dir: abs, depth: current.depth + 1 });
			}
		}
	}

	return out;
}

function canPreviewAsText(absPath: string): boolean {
	const ext = path.extname(absPath).toLowerCase();
	return TEXT_PREVIEW_EXTENSIONS.has(ext);
}

async function readFilePreview(absPath: string): Promise<string> {
	if (!canPreviewAsText(absPath)) {
		return '[preview disabled for this file type]';
	}
	try {
		const raw = await fs.readFile(absPath, 'utf-8');
		const cleaned = raw.split(/\r?\n/).slice(0, 8).join(' ').replace(/\s+/g, ' ').trim();
		if (!cleaned) {
			return '[empty file]';
		}
		return shortOneLine(cleaned, 220);
	} catch {
		return '[preview unavailable]';
	}
}

async function checkDataRaw(): Promise<{
	check: RagLabGuideCheck;
	dataRawPath: string;
	dataRawFileCount: number;
	sampleNoteExists: boolean;
}> {
	const dataRawPath = repoJoin('data/raw');
	const sampleNotePath = repoJoin('data/raw/sample_note.md');
	const dataRawExists = existsSync(dataRawPath);
	const sampleNoteExists = existsSync(sampleNotePath);
	if (!dataRawExists) {
		return {
			check: {
				id: 'data',
				status: 'FAIL',
				detail: `data/raw not found (${dataRawPath})`,
				hint: 'Prepare knowledge files under data/raw.'
			},
			dataRawPath,
			dataRawFileCount: 0,
			sampleNoteExists
		};
	}
	const files = await countFiles(dataRawPath, 3);
	if (files <= 0) {
		return {
			check: {
				id: 'data',
				status: 'WARN',
				detail: `data/raw exists but no files found (${dataRawPath})`,
				hint: 'Add sample files (e.g. sample_note.md) under data/raw.'
			},
			dataRawPath,
			dataRawFileCount: files,
			sampleNoteExists
		};
	}
	return {
		check: {
			id: 'data',
			status: 'PASS',
			detail: `data/raw is ready (${files} file(s))`,
			hint: sampleNoteExists
				? 'Try sample question buttons with sample_note.md.'
				: 'Add sample_note.md for smoother first-run guidance.'
		},
		dataRawPath,
		dataRawFileCount: files,
		sampleNoteExists
	};
}

async function checkIndexDb(): Promise<{
	check: RagLabGuideCheck;
	indexDbPath: string;
	indexDbExists: boolean;
	indexDbSizeBytes: number;
}> {
	const indexDbPath = repoJoin('index/index.sqlite3');
	if (!existsSync(indexDbPath)) {
		return {
			check: {
				id: 'index',
				status: 'FAIL',
				detail: `index DB not found (${indexDbPath})`,
				hint: 'Run ingest/build index before asking local model.'
			},
			indexDbPath,
			indexDbExists: false,
			indexDbSizeBytes: 0
		};
	}
	try {
		const stat = await fs.stat(indexDbPath);
		const size = Math.max(0, Math.trunc(stat.size));
		if (size <= 0) {
			return {
				check: {
					id: 'index',
					status: 'WARN',
					detail: `index DB exists but looks empty (${indexDbPath})`,
					hint: 'Rebuild index and retry.'
				},
				indexDbPath,
				indexDbExists: true,
				indexDbSizeBytes: size
			};
		}
		return {
			check: {
				id: 'index',
				status: 'PASS',
				detail: `index DB exists (${indexDbPath}, ${size} bytes)`,
				hint: 'Index looks ready.'
			},
			indexDbPath,
			indexDbExists: true,
			indexDbSizeBytes: size
		};
	} catch (error) {
		const detail = error instanceof Error ? error.message : String(error);
		return {
			check: {
				id: 'index',
				status: 'FAIL',
				detail: `Failed to inspect index DB: ${shortOneLine(detail)}`,
				hint: 'Verify file permissions and path.'
			},
			indexDbPath,
			indexDbExists: true,
			indexDbSizeBytes: 0
		};
	}
}

export async function getRagLabGuidePayload(): Promise<RagLabGuidePayload> {
	const apiBase =
		resolveLocalModelBackend() === 'gemma_lab'
			? resolveLocalModelRuntimeLabel()
			: resolveOpenAiCompatApiBase(process.env.OPENAI_API_BASE);
	const model = resolveLocalModelName();

	const [llmCheck, dataCheck, indexCheck] = await Promise.all([
		checkLlm(apiBase),
		checkDataRaw(),
		checkIndexDb()
	]);

	const checks: RagLabGuideCheck[] = [llmCheck, dataCheck.check, indexCheck.check];
	const readyToAsk = checks.every((item) => item.status === 'PASS');

	return {
		apiBase,
		model,
		checks,
		dataRawPath: dataCheck.dataRawPath,
		dataRawFileCount: dataCheck.dataRawFileCount,
		indexDbPath: indexCheck.indexDbPath,
		indexDbExists: indexCheck.indexDbExists,
		indexDbSizeBytes: indexCheck.indexDbSizeBytes,
		sampleNoteExists: dataCheck.sampleNoteExists,
		readyToAsk
	};
}

export async function getRagReadonlySnapshotPayload(): Promise<RagReadonlySnapshotPayload> {
	const dataRoot = repoJoin('data/raw');
	const indexDbPath = repoJoin('index/index.sqlite3');

	let files: RagReadonlyFileEntry[] = [];
	let totalFiles = 0;

	if (existsSync(dataRoot)) {
		const absFiles = await listFiles(dataRoot, 4);
		totalFiles = absFiles.length;
		const withMeta = await Promise.all(
			absFiles.map(async (absPath) => {
				try {
					const stat = await fs.stat(absPath);
					return {
						absPath,
						sizeBytes: Math.max(0, Math.trunc(stat.size)),
						modifiedAt: stat.mtime.toISOString()
					};
				} catch {
					return null;
				}
			})
		);
		const normalized = withMeta
			.filter((item): item is NonNullable<typeof item> => item !== null)
			.sort((a, b) => Date.parse(b.modifiedAt) - Date.parse(a.modifiedAt))
			.slice(0, 24);
		files = await Promise.all(
			normalized.map(async (item) => ({
				path: toRepoRelative(item.absPath),
				sizeBytes: item.sizeBytes,
				modifiedAt: item.modifiedAt,
				preview: await readFilePreview(item.absPath)
			}))
		);
	}

	let indexDbExists = false;
	let indexDbSizeBytes = 0;
	if (existsSync(indexDbPath)) {
		indexDbExists = true;
		try {
			const stat = await fs.stat(indexDbPath);
			indexDbSizeBytes = Math.max(0, Math.trunc(stat.size));
		} catch {
			indexDbSizeBytes = 0;
		}
	}

	return {
		generatedAt: new Date().toISOString(),
		dataRoot: toRepoRelative(dataRoot),
		totalFiles,
		files,
		indexDbPath: toRepoRelative(indexDbPath),
		indexDbExists,
		indexDbSizeBytes
	};
}

export async function getRagModelListPayload(): Promise<RagModelListPayload> {
	if (resolveLocalModelBackend() === 'gemma_lab') {
		const probe = await probeGemmaLabRuntime();
		const selectedModel = probe.modelId || resolveLocalModelName();
		return {
			apiBase: resolveLocalModelRuntimeLabel(),
			selectedModel,
			models: [selectedModel],
			resolvedEndpoint: probe.root || null,
			error: probe.status === 'ok' ? null : probe.error || 'gemma-lab runtime unavailable'
		};
	}

	const apiBase = resolveOpenAiCompatApiBase(process.env.OPENAI_API_BASE);
	const selectedModel = resolveLocalModelName();
	const attempts: string[] = [];

	for (const url of modelCheckUrls(apiBase)) {
		const response = await fetchTextWithTimeout(url);
		if (!response.ok) {
			const desc =
				response.status > 0
					? `${url} -> ${response.status}`
					: `${url} -> ${shortOneLine(response.text)}`;
			attempts.push(desc);
			continue;
		}
		return {
			apiBase,
			selectedModel,
			models: modelNamesFromBody(response.text),
			resolvedEndpoint: url,
			error: null
		};
	}

	return {
		apiBase,
		selectedModel,
		models: [],
		resolvedEndpoint: null,
		error: attempts.join(' | ') || 'models endpoint unavailable'
	};
}

export async function writeRagDataAndRebuild(
	request: RagDataWriteRequest
): Promise<RagDataWriteResponse> {
	const fileName = sanitizeFileName(request.fileName);
	const content = (request.content || '').trim();
	if (!content) {
		throw new Error('content is required');
	}

	const rawDir = repoJoin('data/raw');
	await fs.mkdir(rawDir, { recursive: true });
	const absPath = repoJoin('data/raw', fileName);
	await fs.writeFile(absPath, `${content}\n`, 'utf-8');
	const stat = await fs.stat(absPath);

	const shouldRebuild = request.rebuildIndex !== false;
	let rebuild: {
		ran: boolean;
		status: 'PASS' | 'FAIL';
		log: string;
	} = {
		ran: false,
		status: 'PASS',
		log: ''
	};
	if (shouldRebuild) {
		const result = await runBuildIndex();
		rebuild = {
			ran: true,
			status: result.status,
			log: result.log
		};
	}

	return {
		status: rebuild.status,
		savedPath: toRepoRelative(absPath),
		savedBytes: Math.max(0, Math.trunc(stat.size)),
		rebuild,
		snapshot: await getRagReadonlySnapshotPayload()
	};
}
