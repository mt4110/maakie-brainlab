import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

import { afterEach, describe, expect, it } from 'vitest';

import { listRagSourcesReadOnlyFromPaths, rankRagSourcesForText } from './chat-rag-data';
import type { RagSourceItem } from './types';

const BASE_TIME = '2026-03-02T00:00:00.000Z';

function source(input: Partial<RagSourceItem> & { id: string; name: string }): RagSourceItem {
	return {
		id: input.id,
		name: input.name,
		description: input.description ?? '',
		path: input.path ?? '',
		tags: input.tags ?? [],
		enabled: input.enabled ?? true,
		createdAt: input.createdAt ?? BASE_TIME,
		updatedAt: input.updatedAt ?? BASE_TIME
	};
}

const tempDirs: string[] = [];

afterEach(() => {
	for (const dir of tempDirs.splice(0)) {
		rmSync(dir, { recursive: true, force: true });
	}
});

function makeTempStorage() {
	const root = mkdtempSync(path.join(os.tmpdir(), 'brainlab-rag-ro-'));
	tempDirs.push(root);
	const dbPath = path.join(root, '.local/obs/dashboard/rag_sources.sqlite3');
	const legacyPath = path.join(root, '.local/obs/dashboard/rag_sources.json');
	mkdirSync(path.dirname(dbPath), { recursive: true });
	return { root, dbPath, legacyPath };
}

function createSqlite(dbPath: string, items: RagSourceItem[]) {
	const db = new DatabaseSync(dbPath);
	try {
		db.exec(`
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
		`);
		const insert = db.prepare(`
			INSERT INTO rag_sources (
				id, name, description, path, tags_json, enabled, created_at, updated_at
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		`);
		for (const item of items) {
			insert.run(
				item.id,
				item.name,
				item.description,
				item.path,
				JSON.stringify(item.tags),
				item.enabled ? 1 : 0,
				item.createdAt,
				item.updatedAt
			);
		}
	} finally {
		db.close();
	}
}

function writeLegacyJson(legacyPath: string, items: RagSourceItem[]) {
	writeFileSync(legacyPath, JSON.stringify(items, null, 2), 'utf-8');
}

describe('rankRagSourcesForText', () => {
	it('keeps selected boost only for sources that actually match the query', () => {
		const items = [
			source({
				id: 'a',
				name: 'RAG tuning guide',
				path: 'docs/evidence/s25-08/rag_tuning_latest.json',
				description: 'hit_rate and latency tuning',
				tags: ['rag', 'tuning'],
				updatedAt: '2026-03-02T01:00:00.000Z'
			}),
			source({
				id: 'b',
				name: 'RAG operator notes',
				path: 'docs/evidence/s32-15/rag_operator_notes.json',
				description: 'rag operations handbook',
				tags: ['rag', 'ops'],
				updatedAt: '2026-03-02T02:00:00.000Z'
			}),
			source({
				id: 'c',
				name: 'Operator dashboard',
				path: 'docs/evidence/s32-15/operator_dashboard_latest.json',
				description: 'ops metrics',
				tags: ['ops'],
				updatedAt: '2026-03-02T03:00:00.000Z'
			})
		];

		const ranked = rankRagSourcesForText({
			query: 'rag tuning を改善したい',
			sources: items,
			selectedRagIds: ['b', 'c']
		});

		expect(ranked.length).toBe(2);
		expect(ranked[0]?.id).toBe('a');
		expect(ranked[1]?.id).toBe('b');
		expect(ranked[1]?.reason).toContain('selected');
		expect(ranked.some((item) => item.id === 'c')).toBe(false);
	});

	it('ignores disabled sources and keeps only positive matches', () => {
		const ranked = rankRagSourcesForText({
			query: 'langchain retrieval',
			sources: [
				source({
					id: 'x',
					name: 'LangChain PoC',
					path: 'docs/evidence/s25-09/langchain_poc_latest.json',
					tags: ['langchain', 'retrieval']
				}),
				source({
					id: 'y',
					name: 'Disabled Source',
					path: 'docs/evidence/disabled.json',
					tags: ['langchain'],
					enabled: false
				}),
				source({
					id: 'z',
					name: 'Unrelated',
					path: 'docs/evidence/other.json',
					tags: ['misc']
				})
			]
		});

		expect(ranked.length).toBe(1);
		expect(ranked[0]?.id).toBe('x');
	});
});

describe('listRagSourcesReadOnlyFromPaths', () => {
	it('keeps sqlite as the source of truth when the table exists but is empty', async () => {
		const { dbPath, legacyPath } = makeTempStorage();
		createSqlite(dbPath, []);
		writeLegacyJson(legacyPath, [
			source({
				id: 'legacy-1',
				name: 'Legacy Source',
				path: 'docs/evidence/legacy.json',
				tags: ['legacy']
			})
		]);

		const result = await listRagSourcesReadOnlyFromPaths({ dbPath, legacyPath });

		expect(result.degraded).toBe(false);
		expect(result.items).toEqual([]);

		const db = new DatabaseSync(dbPath, { readOnly: true });
		try {
			const row = db.prepare('SELECT COUNT(1) AS n FROM rag_sources').get() as
				| { n?: number }
				| undefined;
			expect(Number(row?.n ?? 0)).toBe(0);
		} finally {
			db.close();
		}
	});

	it('returns legacy JSON items when sqlite does not exist yet', async () => {
		const { dbPath, legacyPath } = makeTempStorage();
		writeLegacyJson(legacyPath, [
			source({
				id: 'legacy-1',
				name: 'Legacy Source',
				path: 'docs/evidence/legacy.json',
				tags: ['legacy']
			})
		]);

		const result = await listRagSourcesReadOnlyFromPaths({ dbPath, legacyPath });

		expect(result.degraded).toBe(false);
		expect(result.items.map((item) => item.id)).toEqual(['legacy-1']);
	});

	it('uses sqlite results when sqlite already has rows', async () => {
		const { dbPath, legacyPath } = makeTempStorage();
		createSqlite(dbPath, [
			source({
				id: 'sqlite-1',
				name: 'SQLite Source',
				path: 'docs/evidence/sqlite.json',
				tags: ['sqlite']
			})
		]);
		writeLegacyJson(legacyPath, [
			source({
				id: 'legacy-1',
				name: 'Legacy Source',
				path: 'docs/evidence/legacy.json',
				tags: ['legacy']
			})
		]);

		const result = await listRagSourcesReadOnlyFromPaths({ dbPath, legacyPath });

		expect(result.degraded).toBe(false);
		expect(result.items.map((item) => item.id)).toEqual(['sqlite-1']);
	});

	it('returns an empty state when sqlite and legacy JSON are both missing', async () => {
		const { dbPath, legacyPath } = makeTempStorage();

		const result = await listRagSourcesReadOnlyFromPaths({ dbPath, legacyPath });

		expect(result.degraded).toBe(false);
		expect(result.items).toEqual([]);
		expect(result.message).toBeNull();
	});
});
