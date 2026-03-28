import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

import { asString, repoJoin } from './fs';
import { postOpenAiCompatChat, resolveOpenAiCompatApiBase } from './openai-compat';
import {
	recordRunInspector,
	summarizeFailureReason,
	type RunInspectorMessageInput,
	type RunInspectorRetrievalInput
} from './run-inspector-data';
import type {
	ChatRunRequest,
	ChatRunResponse,
	ChatTurn,
	DashboardStatus,
	RagSourceCreateRequest,
	RagSourceItem,
	RagSourceUpdateRequest,
	RagSuggestion
} from './types';

const RAG_SOURCES_DB_FILE = repoJoin('.local/obs/dashboard/rag_sources.sqlite3');
const LEGACY_RAG_SOURCES_FILE = repoJoin('.local/obs/dashboard/rag_sources.json');
const CHAT_RUNS_FILE = repoJoin('.local/obs/dashboard/chat_runs.jsonl');
const OUTPUT_LIMIT = 120_000;

interface RagSourceRow {
	id: string;
	name: string;
	description: string;
	path: string;
	tags_json: string;
	enabled: number;
	created_at: string;
	updated_at: string;
}

let ragDb: DatabaseSync | null = null;
let ragStorageInitialized = false;

export interface RagSourceQueryOptions {
	query?: string;
	page?: number;
	pageSize?: number;
}

export interface RagSourceQueryResult {
	items: RagSourceItem[];
	total: number;
	page: number;
	pageSize: number;
	totalPages: number;
	query: string;
}

interface ChatRunLogRecord {
	id: string;
	createdAt: string;
	status: DashboardStatus;
	message: string;
	assistantMessage: string;
	apiBase: string;
	model: string;
	durationMs: number;
	selectedRagIds: string[];
	suggestions: RagSuggestion[];
	error?: string;
}

export interface RagSourceReadOnlyResult {
	items: RagSourceItem[];
	degraded: boolean;
	message: string | null;
}

function trimOutput(text: string): string {
	if (text.length <= OUTPUT_LIMIT) {
		return text;
	}
	return `${text.slice(0, OUTPUT_LIMIT)}\n...[truncated]`;
}

async function appendJsonl(absPath: string, row: Record<string, unknown>): Promise<void> {
	await fs.mkdir(path.dirname(absPath), { recursive: true });
	await fs.appendFile(absPath, `${JSON.stringify(row)}\n`, 'utf-8');
}

function parseTags(input: string[] | string | undefined): string[] {
	if (!input) {
		return [];
	}
	const base = Array.isArray(input) ? input : input.split(/[,\n]/);
	const out: string[] = [];
	for (const raw of base) {
		const tag = asString(raw).trim();
		if (!tag) {
			continue;
		}
		if (!out.includes(tag)) {
			out.push(tag);
		}
	}
	return out.slice(0, 24);
}

function parseTagsFromDb(raw: string): string[] {
	const text = asString(raw).trim();
	if (!text) {
		return [];
	}
	try {
		const parsed = JSON.parse(text);
		if (Array.isArray(parsed)) {
			return parseTags(parsed as string[]);
		}
	} catch {
		// no-op
	}
	return [];
}

function normalizeSource(item: Partial<RagSourceItem>): RagSourceItem | null {
	const id = asString(item.id).trim();
	const name = asString(item.name).trim();
	if (!id || !name) {
		return null;
	}
	const createdAt = asString(item.createdAt).trim() || new Date().toISOString();
	const updatedAt = asString(item.updatedAt).trim() || createdAt;
	return {
		id,
		name,
		description: asString(item.description).trim(),
		path: asString(item.path).trim(),
		tags: parseTags(item.tags as string[] | string | undefined),
		enabled: item.enabled !== false,
		createdAt,
		updatedAt
	};
}

function rowToSource(row: RagSourceRow): RagSourceItem | null {
	return normalizeSource({
		id: row.id,
		name: row.name,
		description: row.description,
		path: row.path,
		tags: parseTagsFromDb(row.tags_json),
		enabled: Number(row.enabled) !== 0,
		createdAt: row.created_at,
		updatedAt: row.updated_at
	});
}

function ensureRagStorage(): DatabaseSync {
	if (ragDb) {
		if (!ragStorageInitialized) {
			importLegacyJsonIfNeeded(ragDb);
			ragStorageInitialized = true;
		}
		return ragDb;
	}
	mkdirSync(path.dirname(RAG_SOURCES_DB_FILE), { recursive: true });
	const db = new DatabaseSync(RAG_SOURCES_DB_FILE);
	db.exec(`
		PRAGMA journal_mode = WAL;
		PRAGMA synchronous = NORMAL;
		PRAGMA busy_timeout = 5000;
		CREATE TABLE IF NOT EXISTS rag_sources (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '',
			path TEXT NOT NULL DEFAULT '',
			tags_json TEXT NOT NULL DEFAULT '[]',
			enabled INTEGER NOT NULL DEFAULT 1,
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL
		);
		CREATE INDEX IF NOT EXISTS idx_rag_sources_updated_at ON rag_sources(updated_at DESC);
		CREATE INDEX IF NOT EXISTS idx_rag_sources_name ON rag_sources(name);
	`);
	ragDb = db;
	if (!ragStorageInitialized) {
		importLegacyJsonIfNeeded(db);
		ragStorageInitialized = true;
	}
	return db;
}

function importLegacyJsonIfNeeded(db: DatabaseSync): void {
	const row = db.prepare('SELECT COUNT(1) AS n FROM rag_sources').get() as
		| { n?: number }
		| undefined;
	const count = Number(row?.n ?? 0);
	if (count > 0) {
		return;
	}
	if (!existsSync(LEGACY_RAG_SOURCES_FILE)) {
		return;
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(readFileSync(LEGACY_RAG_SOURCES_FILE, 'utf-8'));
	} catch {
		return;
	}
	if (!Array.isArray(parsed)) {
		return;
	}

	const insert = db.prepare(`
		INSERT INTO rag_sources (
			id, name, description, path, tags_json, enabled, created_at, updated_at
		) VALUES (
			:id, :name, :description, :path, :tags_json, :enabled, :created_at, :updated_at
		)
		ON CONFLICT(id) DO UPDATE SET
			name=excluded.name,
			description=excluded.description,
			path=excluded.path,
			tags_json=excluded.tags_json,
			enabled=excluded.enabled,
			updated_at=excluded.updated_at
	`);

	db.exec('BEGIN');
	try {
		for (const item of parsed) {
			if (!item || typeof item !== 'object' || Array.isArray(item)) {
				continue;
			}
			const normalized = normalizeSource(item as Partial<RagSourceItem>);
			if (!normalized) {
				continue;
			}
			insert.run({
				id: normalized.id,
				name: normalized.name,
				description: normalized.description,
				path: normalized.path,
				tags_json: JSON.stringify(normalized.tags),
				enabled: normalized.enabled ? 1 : 0,
				created_at: normalized.createdAt,
				updated_at: normalized.updatedAt
			});
		}
		db.exec('COMMIT');
	} catch (error) {
		db.exec('ROLLBACK');
		throw error;
	}
}

function escapeSqlLike(value: string): string {
	return value.replaceAll('\\', '\\\\').replaceAll('%', '\\%').replaceAll('_', '\\_');
}

async function readRagSourcesUnsafe(): Promise<RagSourceItem[]> {
	const db = ensureRagStorage();
	return readRagSourcesFromDb(db);
}

function readRagSourcesFromDb(db: DatabaseSync): RagSourceItem[] {
	const rawRows = db
		.prepare(
			`SELECT id, name, description, path, tags_json, enabled, created_at, updated_at
			 FROM rag_sources
			 ORDER BY updated_at DESC, id ASC`
		)
		.all() as unknown as RagSourceRow[];
	const out: RagSourceItem[] = [];
	for (const item of rawRows) {
		const normalized = rowToSource(item);
		if (normalized) {
			out.push(normalized);
		}
	}
	return out;
}

function readLegacyRagSourcesFileFromPath(legacyPath: string): RagSourceItem[] {
	if (!existsSync(legacyPath)) {
		return [];
	}
	let parsed: unknown;
	try {
		parsed = JSON.parse(readFileSync(legacyPath, 'utf-8'));
	} catch {
		return [];
	}
	if (!Array.isArray(parsed)) {
		return [];
	}
	const out: RagSourceItem[] = [];
	for (const item of parsed) {
		if (!item || typeof item !== 'object' || Array.isArray(item)) {
			continue;
		}
		const normalized = normalizeSource(item as Partial<RagSourceItem>);
		if (normalized) {
			out.push(normalized);
		}
	}
	out.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
	return out;
}

function tokenize(text: string): string[] {
	const raw = (text.toLowerCase().match(/[a-z0-9._/-]+|[ぁ-んァ-ンー一-龯]{2,}/g) || []).map(
		(item) => item.trim()
	);
	const stop = new Set([
		'the',
		'and',
		'for',
		'with',
		'this',
		'that',
		'from',
		'into',
		'about',
		'is',
		'are',
		'what',
		'how',
		'where',
		'when',
		'to',
		'of',
		'を',
		'が',
		'は',
		'に',
		'の',
		'で',
		'と',
		'や',
		'です',
		'ます',
		'こと',
		'ください'
	]);
	const out: string[] = [];
	for (const token of raw) {
		if (token.length < 2) {
			continue;
		}
		if (stop.has(token)) {
			continue;
		}
		if (!out.includes(token)) {
			out.push(token);
		}
	}
	return out.slice(0, 24);
}

function makeReason(parts: string[]): string {
	const unique: string[] = [];
	for (const part of parts) {
		const text = part.trim();
		if (!text) {
			continue;
		}
		if (!unique.includes(text)) {
			unique.push(text);
		}
	}
	return unique.slice(0, 3).join(', ');
}

export function rankRagSourcesForText(args: {
	query: string;
	sources: RagSourceItem[];
	selectedRagIds?: string[];
	limit?: number;
}): RagSuggestion[] {
	const tokens = tokenize(args.query);
	const selected = new Set((args.selectedRagIds || []).map((id) => id.trim()).filter(Boolean));
	const rows: Array<RagSuggestion & { updatedAt: string }> = [];

	for (const source of args.sources) {
		if (!source.enabled) {
			continue;
		}
		const nameLower = source.name.toLowerCase();
		const pathLower = source.path.toLowerCase();
		const descLower = source.description.toLowerCase();
		const tagsLower = source.tags.map((tag) => tag.toLowerCase());
		let score = 0;
		let matched = false;
		const reasons: string[] = [];

		for (const token of tokens) {
			const inName = nameLower.includes(token);
			const inPath = pathLower.includes(token);
			const inDesc = descLower.includes(token);
			const inTags = tagsLower.some((tag) => tag.includes(token));
			if (inName || inPath || inDesc || inTags) {
				matched = true;
			}
			if (inName) {
				score += 4;
				reasons.push(`name:${token}`);
			}
			if (inTags) {
				score += 3;
				reasons.push(`tag:${token}`);
			}
			if (inPath) {
				score += 2;
				reasons.push(`path:${token}`);
			}
			if (inDesc) {
				score += 1;
				reasons.push(`desc:${token}`);
			}
		}

		// Manual selection should reorder already-relevant sources, not fabricate relevance.
		if (!matched) {
			continue;
		}
		if (selected.has(source.id)) {
			score += 2;
			reasons.unshift('selected');
		}

		rows.push({
			id: source.id,
			name: source.name,
			path: source.path,
			tags: source.tags,
			score,
			reason: makeReason(reasons),
			updatedAt: source.updatedAt
		});
	}

	rows.sort((a, b) => {
		if (b.score !== a.score) {
			return b.score - a.score;
		}
		return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
	});

	const limit = Math.max(1, Math.min(8, args.limit ?? 5));
	return rows.slice(0, limit).map(({ updatedAt: _updatedAt, ...rest }) => rest);
}

function sanitizeTurns(input: ChatTurn[] | undefined): ChatTurn[] {
	if (!Array.isArray(input)) {
		return [];
	}
	const out: ChatTurn[] = [];
	for (const row of input) {
		const role = asString(row?.role).trim();
		const content = asString(row?.content).trim();
		if (!content) {
			continue;
		}
		if (role !== 'system' && role !== 'user' && role !== 'assistant') {
			continue;
		}
		out.push({ role, content });
	}
	return out.slice(-14);
}

export async function listRagSources(): Promise<RagSourceItem[]> {
	return readRagSourcesUnsafe();
}

export async function listRagSourcesReadOnlyFromPaths(paths: {
	dbPath: string;
	legacyPath: string;
}): Promise<RagSourceReadOnlyResult> {
	if (!existsSync(paths.dbPath)) {
		return {
			items: readLegacyRagSourcesFileFromPath(paths.legacyPath),
			degraded: false,
			message: null
		};
	}

	try {
		const db = new DatabaseSync(paths.dbPath, {
			readOnly: true,
			timeout: 5000
		});
		try {
			const dbItems = readRagSourcesFromDb(db);
			if (dbItems.length > 0) {
				return {
					items: dbItems,
					degraded: false,
					message: null
				};
			}
			const legacyItems = readLegacyRagSourcesFileFromPath(paths.legacyPath);
			return {
				items: legacyItems,
				degraded: false,
				message: null
			};
		} finally {
			db.close();
		}
	} catch {
		const fallback = readLegacyRagSourcesFileFromPath(paths.legacyPath);
		return {
			items: fallback,
			degraded: true,
			message:
				fallback.length > 0
					? 'Could not read the main storage for the documents list, so a previously saved simplified list is being shown. / 資料一覧の保存領域を直接読めなかったため、保存済みの簡易一覧を表示しています。'
					: 'Could not read the main storage for the documents list, so an empty list is being shown for now. / 資料一覧の保存領域を読めなかったため、現在は空の一覧を表示しています。'
		};
	}
}

export async function listRagSourcesReadOnly(): Promise<RagSourceReadOnlyResult> {
	return listRagSourcesReadOnlyFromPaths({
		dbPath: RAG_SOURCES_DB_FILE,
		legacyPath: LEGACY_RAG_SOURCES_FILE
	});
}

export async function queryRagSources(
	options: RagSourceQueryOptions = {}
): Promise<RagSourceQueryResult> {
	const db = ensureRagStorage();
	const query = asString(options.query).trim().toLowerCase();
	const escaped = escapeSqlLike(query);
	const pattern = `%${escaped}%`;
	const pageSize = Math.max(5, Math.min(100, Math.trunc(options.pageSize ?? 12)));
	const totalRow =
		query.length === 0
			? (db.prepare('SELECT COUNT(1) AS n FROM rag_sources').get() as
					| { n?: number }
					| undefined)
			: (db
					.prepare(
						`SELECT COUNT(1) AS n
						 FROM rag_sources
						 WHERE lower(name) LIKE ? ESCAPE '\\'
						    OR lower(path) LIKE ? ESCAPE '\\'
						    OR lower(description) LIKE ? ESCAPE '\\'
						    OR lower(tags_json) LIKE ? ESCAPE '\\'`
					)
					.get(pattern, pattern, pattern, pattern) as { n?: number } | undefined);
	const total = Number(totalRow?.n ?? 0);
	const totalPages = Math.max(1, Math.ceil(total / pageSize));
	const page = Math.max(1, Math.min(totalPages, Math.trunc(options.page ?? 1)));
	const start = (page - 1) * pageSize;
	const rawRows =
		query.length === 0
			? (db
					.prepare(
						`SELECT id, name, description, path, tags_json, enabled, created_at, updated_at
						 FROM rag_sources
						 ORDER BY updated_at DESC, id ASC
						 LIMIT ? OFFSET ?`
					)
					.all(pageSize, start) as unknown as RagSourceRow[])
			: (db
					.prepare(
						`SELECT id, name, description, path, tags_json, enabled, created_at, updated_at
						 FROM rag_sources
						 WHERE lower(name) LIKE ? ESCAPE '\\'
						    OR lower(path) LIKE ? ESCAPE '\\'
						    OR lower(description) LIKE ? ESCAPE '\\'
						    OR lower(tags_json) LIKE ? ESCAPE '\\'
						 ORDER BY updated_at DESC, id ASC
						 LIMIT ? OFFSET ?`
					)
					.all(
						pattern,
						pattern,
						pattern,
						pattern,
						pageSize,
						start
					) as unknown as RagSourceRow[]);
	const items = rawRows
		.map((row) => rowToSource(row))
		.filter((item): item is RagSourceItem => item !== null);

	return {
		items,
		total,
		page,
		pageSize,
		totalPages,
		query
	};
}

export async function createRagSource(request: RagSourceCreateRequest): Promise<RagSourceItem> {
	const db = ensureRagStorage();
	const name = asString(request.name).trim();
	if (!name) {
		throw new Error('name is required');
	}
	const now = new Date().toISOString();
	const item: RagSourceItem = {
		id: randomUUID(),
		name,
		description: asString(request.description).trim(),
		path: asString(request.path).trim(),
		tags: parseTags(request.tags),
		enabled: request.enabled !== false,
		createdAt: now,
		updatedAt: now
	};
	db.prepare(
		`INSERT INTO rag_sources (
			id, name, description, path, tags_json, enabled, created_at, updated_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
	).run(
		item.id,
		item.name,
		item.description,
		item.path,
		JSON.stringify(item.tags),
		item.enabled ? 1 : 0,
		item.createdAt,
		item.updatedAt
	);
	return item;
}

export async function updateRagSource(
	id: string,
	request: RagSourceUpdateRequest
): Promise<RagSourceItem | null> {
	const db = ensureRagStorage();
	const sourceId = id.trim();
	if (!sourceId) {
		return null;
	}
	const row = db
		.prepare(
			`SELECT id, name, description, path, tags_json, enabled, created_at, updated_at
			 FROM rag_sources
			 WHERE id = ?`
		)
		.get(sourceId) as RagSourceRow | undefined;
	const current = row ? rowToSource(row) : null;
	if (!current) {
		return null;
	}
	const nextName = request.name === undefined ? current.name : asString(request.name).trim();
	if (!nextName) {
		throw new Error('name cannot be empty');
	}
	const updated: RagSourceItem = {
		...current,
		name: nextName,
		description:
			request.description === undefined
				? current.description
				: asString(request.description).trim(),
		path: request.path === undefined ? current.path : asString(request.path).trim(),
		tags: request.tags === undefined ? current.tags : parseTags(request.tags),
		enabled: request.enabled === undefined ? current.enabled : request.enabled,
		updatedAt: new Date().toISOString()
	};
	db.prepare(
		`UPDATE rag_sources
		 SET name = ?, description = ?, path = ?, tags_json = ?, enabled = ?, updated_at = ?
		 WHERE id = ?`
	).run(
		updated.name,
		updated.description,
		updated.path,
		JSON.stringify(updated.tags),
		updated.enabled ? 1 : 0,
		updated.updatedAt,
		sourceId
	);
	return updated;
}

export async function deleteRagSource(id: string): Promise<boolean> {
	const db = ensureRagStorage();
	const sourceId = id.trim();
	if (!sourceId) {
		return false;
	}
	const result = db.prepare('DELETE FROM rag_sources WHERE id = ?').run(sourceId) as {
		changes?: number;
	};
	return Number(result.changes ?? 0) > 0;
}

function buildSystemPrompt(suggestions: RagSuggestion[]): string {
	const lines = [
		'You are a pragmatic AI engineering assistant.',
		'Use concise Japanese by default unless user writes clearly in another language.',
		'When confidence is limited, clearly state uncertainty.',
		'If relevant, propose concrete next actions.'
	];
	if (suggestions.length > 0) {
		lines.push('');
		lines.push('Candidate RAG sources available in workspace:');
		for (const item of suggestions) {
			const tags = item.tags.length > 0 ? ` tags=${item.tags.join('|')}` : '';
			lines.push(`- ${item.name} (${item.path})${tags}`);
		}
		lines.push(
			'If any source appears relevant, explicitly mention it as a suggested reference.'
		);
	}
	return lines.join('\n');
}

function buildInspectorMessages(
	history: ChatTurn[],
	message: string,
	assistantMessage: string
): RunInspectorMessageInput[] {
	const rows: RunInspectorMessageInput[] = [];
	let seq = 0;
	for (const item of history) {
		rows.push({
			seq,
			role: item.role,
			content: item.content
		});
		seq += 1;
	}
	rows.push({
		seq,
		role: 'user',
		content: message
	});
	seq += 1;
	if (assistantMessage.trim()) {
		rows.push({
			seq,
			role: 'assistant',
			content: assistantMessage
		});
	}
	return rows;
}

function suggestionsToRetrievals(items: RagSuggestion[]): RunInspectorRetrievalInput[] {
	return items.slice(0, 24).map((item, index) => ({
		seq: index,
		sourceId: item.id,
		sourcePath: item.path,
		chunkText: item.name,
		score: item.score,
		reason: item.reason || 'rag-suggestion'
	}));
}

export async function runChatWithRag(request: ChatRunRequest): Promise<ChatRunResponse> {
	const message = asString(request.message).trim();
	if (!message) {
		throw new Error('message is required');
	}

	const sources = await readRagSourcesUnsafe();
	const suggestions = rankRagSourcesForText({
		query: message,
		sources,
		selectedRagIds: request.selectedRagIds,
		limit: 5
	});

	const apiBase = resolveOpenAiCompatApiBase(process.env.OPENAI_API_BASE);
	const model = (process.env.LOCAL_GGUF_MODEL || 'Qwen2.5-7B-Instruct').trim();
	const apiKey = (process.env.OPENAI_API_KEY || 'dummy').trim();
	const history = sanitizeTurns(request.messages);
	const systemPrompt = buildSystemPrompt(suggestions);
	const startedAt = Date.now();
	const runId = randomUUID();

	const messages = [
		{ role: 'system', content: systemPrompt },
		...history.map((item) => ({ role: item.role, content: item.content })),
		{ role: 'user', content: message }
	];

	try {
		const chat = await postOpenAiCompatChat({
			apiBase,
			apiKey,
			model,
			temperature: 0.2,
			messages
		});
		const assistantMessage = trimOutput(chat.content);
		const resolvedApiBase = chat.resolvedUrl.replace(/\/chat\/completions$/, '');

		const log: ChatRunLogRecord = {
			id: runId,
			createdAt: new Date().toISOString(),
			status: 'PASS',
			message,
			assistantMessage,
			apiBase: resolvedApiBase,
			model,
			durationMs: Date.now() - startedAt,
			selectedRagIds: request.selectedRagIds || [],
			suggestions
		};
		await appendJsonl(CHAT_RUNS_FILE, log as unknown as Record<string, unknown>);
		let inspector: ChatRunResponse['inspector'];
		try {
			inspector = await recordRunInspector({
				id: runId,
				scope: 'chat-lab',
				source: 'chat-rag',
				status: 'PASS',
				createdAt: log.createdAt,
				prompt: message,
				outputText: assistantMessage,
				command: 'POST /api/dashboard/chat/run',
				model,
				apiBase: resolvedApiBase,
				durationMs: log.durationMs,
				metadata: {
					selectedRagIds: request.selectedRagIds || [],
					suggestionCount: suggestions.length
				},
				messages: buildInspectorMessages(history, message, assistantMessage),
				retrievals: suggestionsToRetrievals(suggestions)
			});
		} catch {
			inspector = undefined;
		}

		return {
			status: 'PASS',
			assistantMessage,
			ragSuggestions: suggestions,
			model,
			apiBase: resolvedApiBase,
			runId,
			inspector
		};
	} catch (error) {
		const text = error instanceof Error ? error.message : 'chat run failed';
		const log: ChatRunLogRecord = {
			id: runId,
			createdAt: new Date().toISOString(),
			status: 'FAIL',
			message,
			assistantMessage: '',
			apiBase,
			model,
			durationMs: Date.now() - startedAt,
			selectedRagIds: request.selectedRagIds || [],
			suggestions,
			error: text
		};
		await appendJsonl(CHAT_RUNS_FILE, log as unknown as Record<string, unknown>);
		try {
			await recordRunInspector({
				id: runId,
				scope: 'chat-lab',
				source: 'chat-rag',
				status: 'FAIL',
				createdAt: log.createdAt,
				prompt: message,
				outputText: '',
				command: 'POST /api/dashboard/chat/run',
				model,
				apiBase,
				durationMs: log.durationMs,
				errorReason: summarizeFailureReason(text),
				metadata: {
					selectedRagIds: request.selectedRagIds || [],
					suggestionCount: suggestions.length
				},
				messages: buildInspectorMessages(history, message, ''),
				retrievals: suggestionsToRetrievals(suggestions)
			});
		} catch {
			// do not override chat error with persistence errors
		}
		throw new Error(text, { cause: error });
	}
}
