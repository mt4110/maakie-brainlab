import { randomUUID } from 'node:crypto';

import { describe, expect, it } from 'vitest';

import {
	extractReferenceRetrievals,
	getLatestRunInspector,
	listRunInspectorHistory,
	recordRunInspector,
	summarizeFailureReason
} from './run-inspector-data';

describe('run-inspector-data helpers', () => {
	it('extracts reference lines from structured answer', () => {
		const text = [
			'結論:',
			'- バナナ価格は100円です',
			'',
			'参照:',
			'- data/raw/sample_note.md:12',
			'- docs/evidence/s25-08/rag_tuning_latest.json'
		].join('\n');
		const rows = extractReferenceRetrievals(text);
		expect(rows.length).toBe(2);
		expect(rows[0]?.sourcePath).toContain('sample_note.md');
		expect(rows[1]?.sourcePath).toContain('rag_tuning_latest.json');
	});

	it('summarizes error text into one reason line', () => {
		const reason = summarizeFailureReason(
			'Traceback ...\nrequests.exceptions.HTTPError: 404 Client Error: Not Found'
		);
		expect(reason).toContain('HTTPError');
	});
});

describe('run-inspector-data storage', () => {
	it('stores and fetches latest run inspector record', async () => {
		const id = randomUUID();
		const createdAt = new Date(Date.now() + 30_000).toISOString();
		await recordRunInspector({
			id,
			scope: 'chat-lab',
			source: 'chat-rag',
			status: 'PASS',
			createdAt,
			prompt: 'test prompt',
			outputText: 'assistant output',
			command: 'POST /api/dashboard/chat/run',
			model: 'Qwen2.5-7B-Instruct',
			apiBase: 'http://127.0.0.1:11434/v1',
			durationMs: 123,
			messages: [
				{ role: 'user', content: 'test prompt' },
				{ role: 'assistant', content: 'assistant output' }
			],
			retrievals: [
				{
					sourceId: 'rag-1',
					sourcePath: 'docs/evidence/sample.json',
					chunkText: 'sample',
					score: 0.9,
					reason: 'name:sample'
				}
			]
		});

		const latest = await getLatestRunInspector('chat-lab');
		expect(latest).not.toBeNull();
		expect(latest?.id).toBe(id);
		expect(latest?.messages.length).toBeGreaterThan(0);
		expect(latest?.retrievals.length).toBe(1);
	});

	it('lists run inspector history rows with scope filter', async () => {
		const rows = await listRunInspectorHistory(20, 'chat-lab');
		expect(rows.length).toBeGreaterThan(0);
		expect(rows.every((row) => row.scope === 'chat-lab')).toBe(true);
		expect(rows[0]?.summary.length).toBeGreaterThan(0);
	});
});
