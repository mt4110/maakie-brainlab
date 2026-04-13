import { describe, expect, it } from 'vitest';

import { buildQuestionGuidance, deriveQuestionExamples, deriveQuestionScopeChips } from './asking';
import type { PresentedQuestionRun } from './presenter';
import type { RagSourceItem } from '$lib/server/types';

function makeSource(input: Partial<RagSourceItem>): RagSourceItem {
	return {
		id: input.id ?? 'source-1',
		name: input.name ?? 'Official Product Requirements',
		description: input.description ?? '',
		path: input.path ?? 'PRODUCT.md',
		tags: input.tags ?? ['product'],
		enabled: input.enabled ?? true,
		createdAt: input.createdAt ?? '2026-03-30T00:00:00.000Z',
		updatedAt: input.updatedAt ?? '2026-03-30T00:00:00.000Z'
	};
}

function makeResult(input: Partial<PresentedQuestionRun> = {}): PresentedQuestionRun {
	return {
		kind: input.kind ?? 'unknown',
		answer: input.answer ?? '',
		evidence: input.evidence ?? [],
		documentsUsed: input.documentsUsed ?? [],
		notices: input.notices ?? []
	};
}

describe('deriveQuestionScopeChips', () => {
	it('adds a neutral no-scope option before current documents', () => {
		const chips = deriveQuestionScopeChips(
			[
				makeSource({ id: 'product' }),
				makeSource({ id: 'architecture', name: 'Official System Architecture', path: 'ARCHITECTURE.md' })
			],
			'ja'
		);

		expect(chips[0]).toEqual({ label: '指定しない', sourceId: null });
		expect(chips[1]?.label).toBe('Official Product Requirements');
	});
});

describe('deriveQuestionExamples', () => {
	it('creates corpus-aware examples from current sources', () => {
		const examples = deriveQuestionExamples(
			[
				makeSource({ id: 'product' }),
				makeSource({ id: 'architecture', name: 'Official System Architecture', path: 'ARCHITECTURE.md' })
			],
			'ja',
			null
		);

		expect(examples.length).toBeGreaterThanOrEqual(3);
		expect(examples[0]?.text).toContain('Official Product Requirements');
		expect(examples[1]?.text).toContain('Official System Architecture');
	});

	it('focuses examples on the selected optional scope', () => {
		const examples = deriveQuestionExamples(
			[
				makeSource({ id: 'product' }),
				makeSource({ id: 'architecture', name: 'Official System Architecture', path: 'ARCHITECTURE.md' })
			],
			'ja',
			'architecture'
		);

		expect(examples[0]?.sourceId).toBe('architecture');
		expect(examples[0]?.text).toContain('Official System Architecture');
		expect(examples.every((item) => item.sourceId === 'architecture')).toBe(true);
	});
});

describe('buildQuestionGuidance', () => {
	it('detects document-name mismatch from a path-like mention and suggests current docs', () => {
		const guidance = buildQuestionGuidance({
			locale: 'ja',
			question: 'Product.mdでmain pathは何面に整理されている？',
			sources: [makeSource({ id: 'product' })],
			selectedScopeId: null,
			uiState: 'unknown',
			result: makeResult()
		});

		expect(guidance.kind).toBe('name_mismatch');
		expect(guidance.diagnosis).toContain('Product.md');
		expect(guidance.likelyMatches[0]?.name).toBe('Official Product Requirements');
		expect(guidance.reaskSuggestions[0]?.text).toContain('Official Product Requirements');
	});

	it('classifies broad unknown questions separately from weak evidence', () => {
		const guidance = buildQuestionGuidance({
			locale: 'ja',
			question: '大事なことを教えて',
			sources: [
				makeSource({ id: 'product' }),
				makeSource({ id: 'architecture', name: 'Official System Architecture', path: 'ARCHITECTURE.md' })
			],
			selectedScopeId: null,
			uiState: 'unknown',
			result: makeResult({ notices: ['clarify_question'] })
		});

		expect(guidance.kind).toBe('too_broad');
		expect(guidance.reaskSuggestions).toHaveLength(3);
	});

	it('falls back to weak evidence when the question is specific but still unsupported', () => {
		const guidance = buildQuestionGuidance({
			locale: 'ja',
			question: 'Official Product Requirements で main path の役割を教えて',
			sources: [makeSource({ id: 'product' })],
			selectedScopeId: 'product',
			uiState: 'unknown',
			result: makeResult({
				evidence: [
					{
						sourceId: 'product',
						sourceName: 'Official Product Requirements',
						sourcePath: 'PRODUCT.md',
						preview: '',
						matches: [{ kind: 'selected', term: null }]
					}
				]
			})
		});

		expect(guidance.kind).toBe('weak_evidence');
		expect(guidance.reaskSuggestions[0]?.sourceId).toBe('product');
	});
});
