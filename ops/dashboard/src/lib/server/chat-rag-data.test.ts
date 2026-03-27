import { describe, expect, it } from 'vitest';

import { rankRagSourcesForText } from './chat-rag-data';
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
