import { randomUUID } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

import { asNumber, asString, normalizeStatus, repoJoin } from './fs';
import type {
	RunInspectorHistoryItem,
	RunInspectorMessage,
	RunInspectorRecord,
	RunInspectorRetrieval,
	RunInspectorScope,
	RunInspectorVote
} from './types';

const RUN_INSPECTOR_DB_FILE = repoJoin('.local/obs/dashboard/run_inspector.sqlite3');
const TEXT_LIMIT = 120_000;
const RETRIEVAL_LIMIT = 24;
const MESSAGE_LIMIT = 40;
const VOTE_LIMIT = 16;

interface RunRow {
	id: string;
	scope: string;
	source: string;
	status: string;
	created_at: string;
	prompt: string;
	output_text: string;
	command: string;
	model: string;
	api_base: string;
	duration_ms: number;
	error_reason: string;
	metadata_json: string;
}

interface MessageRow {
	seq: number;
	role: string;
	content: string;
}

interface RetrievalRow {
	seq: number;
	source_id: string;
	source_path: string;
	chunk_text: string;
	score: number | null;
	reason: string;
}

interface VoteRow {
	voter: string;
	verdict: string;
	score: number | null;
	rationale: string;
}

interface RunHistoryRow extends RunRow {
	retrieval_count: number;
}

export interface RunInspectorMessageInput {
	seq?: number;
	role: string;
	content: string;
}

export interface RunInspectorRetrievalInput {
	seq?: number;
	sourceId?: string;
	sourcePath?: string;
	chunkText: string;
	score?: number | null;
	reason?: string;
}

export interface RunInspectorVoteInput {
	voter: string;
	verdict: string;
	score?: number | null;
	rationale?: string;
}

export interface RunInspectorWriteInput {
	id: string;
	scope: RunInspectorScope;
	source: string;
	status: string;
	createdAt: string;
	prompt: string;
	outputText: string;
	command?: string;
	model?: string;
	apiBase?: string;
	durationMs?: number | null;
	errorReason?: string;
	metadata?: Record<string, unknown>;
	messages?: RunInspectorMessageInput[];
	retrievals?: RunInspectorRetrievalInput[];
	votes?: RunInspectorVoteInput[];
}

let inspectorDb: DatabaseSync | null = null;

function trimText(value: string, limit = TEXT_LIMIT): string {
	const text = asString(value);
	if (text.length <= limit) {
		return text;
	}
	return `${text.slice(0, limit)}\n...[truncated]`;
}

function normalizeScope(value: string): RunInspectorScope {
	return value === 'chat-lab' ? 'chat-lab' : 'ai-lab';
}

function normalizeRole(value: string): RunInspectorMessage['role'] {
	const role = asString(value).trim().toLowerCase();
	if (role === 'system' || role === 'user' || role === 'assistant' || role === 'tool') {
		return role;
	}
	return 'meta';
}

function normalizeScore(value: unknown): number | null {
	const n = asNumber(value);
	return n === null ? null : n;
}

function detectContextEmptyText(outputText: string, errorReason = ''): boolean {
	const text = `${asString(outputText)}\n${asString(errorReason)}`.toLowerCase();
	return /context[^\n]*空|context\s*is\s*empty/.test(text);
}

function shortReason(text: string, max = 120): string {
	const compact = asString(text).replace(/\s+/g, ' ').trim();
	if (!compact) {
		return '';
	}
	return compact.length <= max ? compact : `${compact.slice(0, max)}...`;
}

function summarizeHistoryRow(
	status: string,
	retrievalCount: number,
	outputText: string,
	errorReason: string
): string {
	const normalized = normalizeStatus(status);
	if (normalized === 'PASS') {
		if (detectContextEmptyText(outputText, errorReason)) {
			return 'PASS: context empty (no evidence retrieved)';
		}
		if (retrievalCount > 0) {
			return `PASS: retrieved ${retrievalCount} chunk(s)`;
		}
		return 'PASS: response returned (0 retrieved chunks)';
	}
	if (normalized === 'WARN') {
		const reason = shortReason(errorReason);
		return reason ? `WARN: ${reason}` : 'WARN: completed with review required';
	}
	const reason = shortReason(errorReason);
	return reason ? `FAIL: ${reason}` : `FAIL: execution failed`;
}

function parseMetadata(raw: string): Record<string, unknown> {
	const text = asString(raw).trim();
	if (!text) {
		return {};
	}
	try {
		const parsed = JSON.parse(text);
		if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
			return parsed as Record<string, unknown>;
		}
	} catch {
		return {};
	}
	return {};
}

function makeDb(): DatabaseSync {
	if (inspectorDb) {
		return inspectorDb;
	}
	mkdirSync(path.dirname(RUN_INSPECTOR_DB_FILE), { recursive: true });
	const db = new DatabaseSync(RUN_INSPECTOR_DB_FILE);
	db.exec(`
		PRAGMA journal_mode = WAL;
		PRAGMA synchronous = NORMAL;
		PRAGMA busy_timeout = 5000;
		PRAGMA foreign_keys = ON;
		CREATE TABLE IF NOT EXISTS runs (
			id TEXT PRIMARY KEY,
			scope TEXT NOT NULL,
			source TEXT NOT NULL,
			status TEXT NOT NULL,
			created_at TEXT NOT NULL,
			prompt TEXT NOT NULL DEFAULT '',
			output_text TEXT NOT NULL DEFAULT '',
			command TEXT NOT NULL DEFAULT '',
			model TEXT NOT NULL DEFAULT '',
			api_base TEXT NOT NULL DEFAULT '',
			duration_ms INTEGER NOT NULL DEFAULT 0,
			error_reason TEXT NOT NULL DEFAULT '',
			metadata_json TEXT NOT NULL DEFAULT '{}'
		);
		CREATE INDEX IF NOT EXISTS idx_runs_scope_created ON runs(scope, created_at DESC);
		CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status, created_at DESC);

		CREATE TABLE IF NOT EXISTS messages (
			id TEXT PRIMARY KEY,
			run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
			seq INTEGER NOT NULL,
			role TEXT NOT NULL,
			content TEXT NOT NULL
		);
		CREATE INDEX IF NOT EXISTS idx_messages_run_seq ON messages(run_id, seq ASC);

		CREATE TABLE IF NOT EXISTS retrievals (
			id TEXT PRIMARY KEY,
			run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
			seq INTEGER NOT NULL,
			source_id TEXT NOT NULL DEFAULT '',
			source_path TEXT NOT NULL DEFAULT '',
			chunk_text TEXT NOT NULL DEFAULT '',
			score REAL,
			reason TEXT NOT NULL DEFAULT ''
		);
		CREATE INDEX IF NOT EXISTS idx_retrievals_run_seq ON retrievals(run_id, seq ASC);

		CREATE TABLE IF NOT EXISTS votes (
			id TEXT PRIMARY KEY,
			run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
			voter TEXT NOT NULL,
			verdict TEXT NOT NULL,
			score REAL,
			rationale TEXT NOT NULL DEFAULT ''
		);
		CREATE INDEX IF NOT EXISTS idx_votes_run ON votes(run_id);
	`);
	inspectorDb = db;
	return db;
}

function rowToRecord(row: RunRow, db: DatabaseSync): RunInspectorRecord {
	const messagesRaw = db
		.prepare(
			`SELECT seq, role, content
			 FROM messages
			 WHERE run_id = ?
			 ORDER BY seq ASC, id ASC`
		)
		.all(row.id) as unknown as MessageRow[];
	const retrievalsRaw = db
		.prepare(
			`SELECT seq, source_id, source_path, chunk_text, score, reason
			 FROM retrievals
			 WHERE run_id = ?
			 ORDER BY seq ASC, id ASC`
		)
		.all(row.id) as unknown as RetrievalRow[];
	const votesRaw = db
		.prepare(
			`SELECT voter, verdict, score, rationale
			 FROM votes
			 WHERE run_id = ?
			 ORDER BY rowid ASC`
		)
		.all(row.id) as unknown as VoteRow[];

	const messages: RunInspectorMessage[] = messagesRaw.map((item) => ({
		seq: Math.max(0, Math.trunc(asNumber(item.seq) ?? 0)),
		role: normalizeRole(item.role),
		content: asString(item.content)
	}));
	const retrievals: RunInspectorRetrieval[] = retrievalsRaw.map((item) => ({
		seq: Math.max(0, Math.trunc(asNumber(item.seq) ?? 0)),
		sourceId: asString(item.source_id).trim(),
		sourcePath: asString(item.source_path).trim(),
		chunkText: asString(item.chunk_text),
		score: normalizeScore(item.score),
		reason: asString(item.reason).trim()
	}));
	const votes: RunInspectorVote[] = votesRaw.map((item) => ({
		voter: asString(item.voter).trim(),
		verdict: asString(item.verdict).trim(),
		score: normalizeScore(item.score),
		rationale: asString(item.rationale)
	}));

	return {
		id: row.id,
		scope: normalizeScope(row.scope),
		source: asString(row.source).trim(),
		status: normalizeStatus(row.status),
		createdAt: asString(row.created_at),
		prompt: asString(row.prompt),
		outputText: asString(row.output_text),
		command: asString(row.command),
		model: asString(row.model),
		apiBase: asString(row.api_base),
		durationMs: Math.max(0, Math.trunc(asNumber(row.duration_ms) ?? 0)),
		errorReason: asString(row.error_reason),
		metadata: parseMetadata(asString(row.metadata_json)),
		messages,
		retrievals,
		votes
	};
}

function canonicalReferences(lines: string[]): string[] {
	const out: string[] = [];
	for (const raw of lines) {
		const line = asString(raw)
			.replace(/^[\s*\-・●○]+/, '')
			.replace(/^\d+[.)]\s+/, '')
			.trim();
		if (!line) {
			continue;
		}
		const lower = line.toLowerCase();
		if (
			lower === '不明' ||
			lower === '不明（参照なし）' ||
			lower === 'none' ||
			lower === '(none)'
		) {
			continue;
		}
		if (!out.includes(line)) {
			out.push(line);
		}
		if (out.length >= RETRIEVAL_LIMIT) {
			break;
		}
	}
	return out;
}

function collectSection(text: string, labels: string[]): string[] {
	const rows = text.split(/\r?\n/);
	const starts = labels.map((label) => new RegExp(`^\\s*${label}\\s*:\\s*`, 'i'));
	const stop =
		/^\s*(結論|conclusion|根拠|evidence|参照|references?|不確実性|uncertainty)\s*:\s*/i;
	let collecting = false;
	const out: string[] = [];
	for (const row of rows) {
		if (!collecting) {
			const match = starts.find((pattern) => pattern.test(row));
			if (!match) {
				continue;
			}
			collecting = true;
			const rest = row.replace(match, '').trim();
			if (rest) {
				out.push(rest);
			}
			continue;
		}
		if (stop.test(row)) {
			break;
		}
		out.push(row);
	}
	return out;
}

function extractPathLike(text: string): string {
	const match = text.match(
		/[A-Za-z0-9_./-]+\.(?:md|txt|json|yaml|yml|toml|csv|py|ts|js|sql|pdf)(?::\d+)?/i
	);
	return match ? match[0] : '';
}

export function extractReferenceRetrievals(text: string): RunInspectorRetrievalInput[] {
	const body = asString(text);
	if (!body.trim()) {
		return [];
	}
	const sectionRows = collectSection(body, ['参照', 'references?']);
	const canonical = canonicalReferences(sectionRows);
	if (canonical.length > 0) {
		return canonical.map((item, index) => ({
			seq: index,
			sourcePath: extractPathLike(item),
			chunkText: item,
			reason: 'reference'
		}));
	}
	const fallbackLines = canonicalReferences(
		body
			.split(/\r?\n/)
			.filter((line) =>
				/[A-Za-z0-9_./-]+\.(?:md|txt|json|yaml|yml|toml|csv|py|ts|js|sql|pdf)/i.test(line)
			)
			.slice(0, RETRIEVAL_LIMIT)
	);
	return fallbackLines.map((item, index) => ({
		seq: index,
		sourcePath: extractPathLike(item),
		chunkText: item,
		reason: 'path-detected'
	}));
}

export function summarizeFailureReason(stderr: string, stdout = ''): string {
	const source = asString(stderr).trim() || asString(stdout).trim();
	if (!source) {
		return '';
	}
	const lines = source
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter(Boolean);
	if (lines.length === 0) {
		return '';
	}
	const preferred =
		lines.find((line) => /(HTTPError|Exception|Error:|failed|timeout|not found)/i.test(line)) ||
		lines.at(-1) ||
		lines[0];
	return trimText(preferred || '', 320);
}

function normalizeMessages(input: RunInspectorMessageInput[] | undefined): RunInspectorMessage[] {
	if (!Array.isArray(input) || input.length === 0) {
		return [];
	}
	const out: RunInspectorMessage[] = [];
	for (let i = 0; i < input.length && out.length < MESSAGE_LIMIT; i += 1) {
		const item = input[i];
		const content = trimText(asString(item?.content).trim());
		if (!content) {
			continue;
		}
		const seq = Math.max(0, Math.trunc(asNumber(item?.seq) ?? out.length));
		out.push({
			seq,
			role: normalizeRole(item?.role),
			content
		});
	}
	out.sort((a, b) => a.seq - b.seq);
	return out;
}

function normalizeRetrievals(
	input: RunInspectorRetrievalInput[] | undefined
): RunInspectorRetrieval[] {
	if (!Array.isArray(input) || input.length === 0) {
		return [];
	}
	const out: RunInspectorRetrieval[] = [];
	for (let i = 0; i < input.length && out.length < RETRIEVAL_LIMIT; i += 1) {
		const item = input[i];
		const chunkText = trimText(asString(item?.chunkText).trim());
		if (!chunkText) {
			continue;
		}
		out.push({
			seq: Math.max(0, Math.trunc(asNumber(item?.seq) ?? out.length)),
			sourceId: asString(item?.sourceId).trim(),
			sourcePath: asString(item?.sourcePath).trim(),
			chunkText,
			score: normalizeScore(item?.score),
			reason: asString(item?.reason).trim()
		});
	}
	out.sort((a, b) => a.seq - b.seq);
	return out;
}

function normalizeVotes(input: RunInspectorVoteInput[] | undefined): RunInspectorVote[] {
	if (!Array.isArray(input) || input.length === 0) {
		return [];
	}
	const out: RunInspectorVote[] = [];
	for (const item of input) {
		if (out.length >= VOTE_LIMIT) {
			break;
		}
		const voter = asString(item?.voter).trim();
		const verdict = asString(item?.verdict).trim();
		if (!voter || !verdict) {
			continue;
		}
		out.push({
			voter,
			verdict,
			score: normalizeScore(item?.score),
			rationale: trimText(asString(item?.rationale), 2000)
		});
	}
	return out;
}

export async function recordRunInspector(
	input: RunInspectorWriteInput
): Promise<RunInspectorRecord> {
	const id = asString(input.id).trim() || randomUUID();
	const scope = normalizeScope(asString(input.scope));
	const source = asString(input.source).trim() || 'unknown';
	const createdAt = asString(input.createdAt).trim() || new Date().toISOString();
	const status = normalizeStatus(input.status);
	const prompt = trimText(asString(input.prompt));
	const outputText = trimText(asString(input.outputText));
	const command = trimText(asString(input.command), 4000);
	const model = trimText(asString(input.model).trim(), 400);
	const apiBase = trimText(asString(input.apiBase).trim(), 400);
	const durationMs = Math.max(0, Math.trunc(asNumber(input.durationMs) ?? 0));
	const errorReason = trimText(asString(input.errorReason).trim(), 1000);
	const metadata = input.metadata && typeof input.metadata === 'object' ? input.metadata : {};
	const messages = normalizeMessages(input.messages);
	const retrievals = normalizeRetrievals(input.retrievals);
	const votes = normalizeVotes(input.votes);
	const metadataJson = trimText(JSON.stringify(metadata), 50_000);

	const db = makeDb();
	db.exec('BEGIN');
	try {
		db.prepare('DELETE FROM runs WHERE id = ?').run(id);
		db.prepare(
			`INSERT INTO runs (
				id, scope, source, status, created_at, prompt, output_text, command, model, api_base, duration_ms, error_reason, metadata_json
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
		).run(
			id,
			scope,
			source,
			status,
			createdAt,
			prompt,
			outputText,
			command,
			model,
			apiBase,
			durationMs,
			errorReason,
			metadataJson
		);

		const insertMessage = db.prepare(
			'INSERT INTO messages (id, run_id, seq, role, content) VALUES (?, ?, ?, ?, ?)'
		);
		for (const item of messages) {
			insertMessage.run(randomUUID(), id, item.seq, item.role, item.content);
		}

		const insertRetrieval = db.prepare(
			`INSERT INTO retrievals (id, run_id, seq, source_id, source_path, chunk_text, score, reason)
			 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
		);
		for (const item of retrievals) {
			insertRetrieval.run(
				randomUUID(),
				id,
				item.seq,
				item.sourceId,
				item.sourcePath,
				item.chunkText,
				item.score,
				item.reason
			);
		}

		const insertVote = db.prepare(
			'INSERT INTO votes (id, run_id, voter, verdict, score, rationale) VALUES (?, ?, ?, ?, ?, ?)'
		);
		for (const item of votes) {
			insertVote.run(randomUUID(), id, item.voter, item.verdict, item.score, item.rationale);
		}
		db.exec('COMMIT');
	} catch (error) {
		db.exec('ROLLBACK');
		throw error;
	}

	const saved = await getRunInspectorById(id);
	if (!saved) {
		throw new Error(`run inspector insert failed: ${id}`);
	}
	return saved;
}

export async function getRunInspectorById(id: string): Promise<RunInspectorRecord | null> {
	const runId = asString(id).trim();
	if (!runId) {
		return null;
	}
	const db = makeDb();
	const row = db
		.prepare(
			`SELECT id, scope, source, status, created_at, prompt, output_text, command, model, api_base, duration_ms, error_reason, metadata_json
			 FROM runs
			 WHERE id = ?`
		)
		.get(runId) as RunRow | undefined;
	if (!row) {
		return null;
	}
	return rowToRecord(row, db);
}

export async function getLatestRunInspector(
	scope: RunInspectorScope
): Promise<RunInspectorRecord | null> {
	const db = makeDb();
	const futureCutoff = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
	const row = db
		.prepare(
			`SELECT id, scope, source, status, created_at, prompt, output_text, command, model, api_base, duration_ms, error_reason, metadata_json
			 FROM runs
			 WHERE scope = ?
			   AND created_at <= ?
			 ORDER BY created_at DESC, rowid DESC
			 LIMIT 1`
		)
		.get(scope, futureCutoff) as RunRow | undefined;
	if (!row) {
		return null;
	}
	return rowToRecord(row, db);
}

export async function listRunInspectorHistory(
	limit = 200,
	scope: RunInspectorScope | 'all' = 'all'
): Promise<RunInspectorHistoryItem[]> {
	const db = makeDb();
	const safeLimit = Math.max(1, Math.min(1000, Math.trunc(limit)));
	const rows = db
		.prepare(
			`SELECT
				r.id,
				r.scope,
				r.source,
				r.status,
				r.created_at,
				r.prompt,
				r.output_text,
				r.command,
				r.model,
				r.api_base,
				r.duration_ms,
				r.error_reason,
				r.metadata_json,
				CAST(COUNT(ret.id) AS INTEGER) AS retrieval_count
			 FROM runs r
			 LEFT JOIN retrievals ret
			   ON ret.run_id = r.id
			 WHERE (? = 'all' OR r.scope = ?)
			 GROUP BY
			 	r.id,
			 	r.scope,
			 	r.source,
			 	r.status,
			 	r.created_at,
			 	r.prompt,
			 	r.output_text,
			 	r.command,
			 	r.model,
			 	r.api_base,
			 	r.duration_ms,
			 	r.error_reason,
			 	r.metadata_json
			 ORDER BY r.created_at DESC, r.rowid DESC
			 LIMIT ?`
		)
		.all(scope, scope, safeLimit) as unknown as RunHistoryRow[];

	const futureCutoff = Date.now() + 24 * 60 * 60 * 1000;
	return rows
		.map((row) => {
			const retrievalCount = Math.max(0, Math.trunc(asNumber(row.retrieval_count) ?? 0));
			return {
				id: row.id,
				scope: normalizeScope(row.scope),
				source: asString(row.source).trim(),
				status: normalizeStatus(row.status),
				createdAt: asString(row.created_at),
				model: asString(row.model),
				apiBase: asString(row.api_base),
				prompt: asString(row.prompt),
				summary: summarizeHistoryRow(
					asString(row.status),
					retrievalCount,
					asString(row.output_text),
					asString(row.error_reason)
				),
				retrievalCount,
				errorReason: asString(row.error_reason)
			};
		})
		.filter((row) => {
			const ts = new Date(row.createdAt).getTime();
			if (!Number.isFinite(ts)) {
				return true;
			}
			return ts <= futureCutoff;
		});
}
