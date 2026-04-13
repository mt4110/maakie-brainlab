import type { Locale } from '$lib/i18n';
import type { RagSourceItem } from '$lib/server/types';

import type { PresentedQuestionRun, QuestionNoticeCode } from './presenter';

export interface QuestionSuggestion {
	text: string;
	sourceId: string | null;
}

export interface QuestionScopeChip {
	label: string;
	sourceId: string | null;
}

export interface QuestionLikelyMatch {
	id: string;
	name: string;
	path: string;
}

export type QuestionGuidanceKind =
	| 'idle'
	| 'answer_ready'
	| 'blank_input'
	| 'no_documents'
	| 'name_mismatch'
	| 'too_broad'
	| 'weak_evidence'
	| 'backend_unavailable'
	| 'server_failure';

export interface QuestionGuidance {
	kind: QuestionGuidanceKind;
	diagnosis: string;
	reaskSuggestions: QuestionSuggestion[];
	likelyMatches: QuestionLikelyMatch[];
}

interface NameMismatchMatch extends QuestionLikelyMatch {
	score: number;
}

interface NameMismatchResult {
	term: string;
	matches: QuestionLikelyMatch[];
}

interface BuildGuidanceInput {
	locale: Locale;
	question: string;
	sources: RagSourceItem[];
	selectedScopeId: string | null;
	uiState:
		| 'idle'
		| 'blank'
		| 'no_documents'
		| 'answer'
		| 'unknown'
		| 'backend_unavailable'
		| 'server_failure';
	result: PresentedQuestionRun | null;
}

function enabledSourcesOnly(sources: RagSourceItem[]): RagSourceItem[] {
	return sources.filter((item) => item.enabled !== false);
}

function normalizeWhitespace(value: string): string {
	return value.replace(/\s+/g, ' ').trim();
}

function normalizeLookup(value: string): string {
	return normalizeWhitespace(value)
		.toLowerCase()
		.normalize('NFKC')
		.replace(/[`"'“”‘’「」\s._/\\-]+/g, '');
}

function basenameLike(pathLike: string): string {
	const compact = normalizeWhitespace(pathLike);
	if (!compact) {
		return '';
	}
	const parts = compact.split('/').filter(Boolean);
	return parts[parts.length - 1] || compact;
}

function displayLabel(item: RagSourceItem): string {
	return normalizeWhitespace(item.name) || basenameLike(item.path) || 'Current document';
}

function dedupeSuggestions(items: QuestionSuggestion[]): QuestionSuggestion[] {
	const seen = new Set<string>();
	const out: QuestionSuggestion[] = [];
	for (const item of items) {
		const text = normalizeWhitespace(item.text);
		if (!text) {
			continue;
		}
		const key = `${item.sourceId ?? 'none'}::${text.toLowerCase()}`;
		if (seen.has(key)) {
			continue;
		}
		seen.add(key);
		out.push({ text, sourceId: item.sourceId });
	}
	return out;
}

function questionFocus(question: string, locale: Locale): string {
	const compact = question.toLowerCase();
	if (/main path/.test(compact)) {
		return 'main path';
	}
	if (/制約/.test(question) || /constraint/.test(compact)) {
		return locale === 'ja' ? '制約' : 'constraints';
	}
	if (/設計|architecture/.test(question) || /architecture|design/.test(compact)) {
		return locale === 'ja' ? '設計判断' : 'design decisions';
	}
	if (/要点|概要|まとめ/.test(question) || /summary|overview|key point/.test(compact)) {
		return locale === 'ja' ? '要点' : 'key points';
	}
	if (/根拠|evidence/.test(question) || /evidence/.test(compact)) {
		return locale === 'ja' ? '根拠' : 'evidence';
	}
	return '';
}

function sourceKind(item: RagSourceItem): 'product' | 'architecture' | 'api' | 'general' {
	const compact = `${item.name} ${item.path} ${item.tags.join(' ')}`.toLowerCase();
	if (/product|requirement|prd/.test(compact)) {
		return 'product';
	}
	if (/architecture|design|system/.test(compact)) {
		return 'architecture';
	}
	if (/api|contract|schema/.test(compact)) {
		return 'api';
	}
	return 'general';
}

function exampleTemplatesForSource(
	item: RagSourceItem,
	locale: Locale,
	focus = ''
): QuestionSuggestion[] {
	const label = displayLabel(item);
	const kind = sourceKind(item);
	const sourceId = item.id;
	if (locale === 'ja') {
		const base =
			focus.length > 0
				? [
						{ text: `${label} で ${focus} はどう整理されていますか？`, sourceId },
						{ text: `${label} の中で ${focus} に関係する点だけ教えてください。`, sourceId }
					]
				: [];
		switch (kind) {
			case 'product':
				return [
					...base,
					{ text: `${label} の要点は？`, sourceId },
					{ text: `${label} で main path はどう整理されていますか？`, sourceId },
					{ text: `${label} にある重要な制約は？`, sourceId }
				];
			case 'architecture':
				return [
					...base,
					{ text: `${label} で重要な設計判断は？`, sourceId },
					{ text: `${label} の構成で先に押さえるべき点は？`, sourceId },
					{ text: `${label} にある制約や前提は？`, sourceId }
				];
			case 'api':
				return [
					...base,
					{ text: `${label} にある重要な制約は？`, sourceId },
					{ text: `${label} で注意すべき入出力は？`, sourceId },
					{ text: `${label} の要点を短く教えてください。`, sourceId }
				];
			default:
				return [
					...base,
					{ text: `${label} の要点は？`, sourceId },
					{ text: `${label} で先に知るべき点は？`, sourceId },
					{ text: `${label} に書かれている注意点は？`, sourceId }
				];
		}
	}
	const base =
		focus.length > 0
			? [
					{ text: `How does ${label} describe ${focus}?`, sourceId },
					{ text: `What does ${label} say about ${focus}?`, sourceId }
				]
			: [];
	switch (kind) {
		case 'product':
			return [
				...base,
				{ text: `What are the key points in ${label}?`, sourceId },
				{ text: `How does ${label} organize the main path?`, sourceId },
				{ text: `What important constraints appear in ${label}?`, sourceId }
			];
		case 'architecture':
			return [
				...base,
				{ text: `What major design decisions appear in ${label}?`, sourceId },
				{ text: `What should I understand first in ${label}?`, sourceId },
				{ text: `What constraints or assumptions appear in ${label}?`, sourceId }
			];
		case 'api':
			return [
				...base,
				{ text: `What important constraints appear in ${label}?`, sourceId },
				{ text: `What inputs and outputs matter in ${label}?`, sourceId },
				{ text: `What are the key points in ${label}?`, sourceId }
			];
		default:
			return [
				...base,
				{ text: `What are the key points in ${label}?`, sourceId },
				{ text: `What should I understand first in ${label}?`, sourceId },
				{ text: `What cautions appear in ${label}?`, sourceId }
			];
	}
}

function sourceById(sources: RagSourceItem[], sourceId: string | null): RagSourceItem | null {
	if (!sourceId) {
		return null;
	}
	return sources.find((item) => item.id === sourceId) ?? null;
}

function tokenizeForOverlap(value: string): string[] {
	return (value.toLowerCase().match(/[a-z0-9]+|[ぁ-んァ-ンー一-龯]{2,}/g) || []).map((item) =>
		item.trim()
	);
}

function scorePotentialMatch(term: string, item: RagSourceItem): number {
	const normalizedTerm = normalizeLookup(term);
	if (!normalizedTerm) {
		return 0;
	}
	const nameNorm = normalizeLookup(item.name);
	const pathNorm = normalizeLookup(item.path);
	const baseNorm = normalizeLookup(basenameLike(item.path));
	if (nameNorm === normalizedTerm) {
		return 100;
	}
	if (pathNorm === normalizedTerm || baseNorm === normalizedTerm) {
		return 90;
	}
	if (nameNorm.includes(normalizedTerm) || normalizedTerm.includes(nameNorm)) {
		return 72;
	}
	if (pathNorm.includes(normalizedTerm) || baseNorm.includes(normalizedTerm)) {
		return 68;
	}
	const sourceTokens = new Set([
		...tokenizeForOverlap(item.name),
		...tokenizeForOverlap(basenameLike(item.path))
	]);
	const overlap = tokenizeForOverlap(term).filter((token) => sourceTokens.has(token)).length;
	return overlap > 0 ? overlap * 18 : 0;
}

function extractDocumentLikeTerms(question: string): string[] {
	const out = new Set<string>();
	for (const match of question.matchAll(/\b[A-Za-z0-9_./-]+\.(?:md|txt|pdf|docx?|csv|json|ya?ml)\b/gi)) {
		out.add(match[0]);
	}
	for (const match of question.matchAll(/[「"']([^「」"']{2,80})[」"']/g)) {
		const inner = normalizeWhitespace(match[1] || '');
		if (/document|doc|requirements|architecture|api|spec|資料|要件|設計|契約/i.test(inner)) {
			out.add(inner);
		}
	}
	return Array.from(out);
}

function detectNameMismatch(question: string, sources: RagSourceItem[]): NameMismatchResult | null {
	const enabled = enabledSourcesOnly(sources);
	for (const term of extractDocumentLikeTerms(question)) {
		const normalizedTerm = normalizeLookup(term);
		const exactName = enabled.some((item) => normalizeLookup(item.name) === normalizedTerm);
		if (exactName) {
			continue;
		}
		const matches = enabled
			.map((item) => ({
				id: item.id,
				name: displayLabel(item),
				path: item.path,
				score: scorePotentialMatch(term, item)
			}))
			.filter((item): item is NameMismatchMatch => item.score > 0)
			.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name))
			.slice(0, 3)
			.map(({ score: _, ...item }) => item);
		if (matches.length > 0) {
			return { term, matches };
		}
	}
	return null;
}

function escapeRegExp(value: string): string {
	return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function rewriteQuestion(question: string, rawTerm: string, replacement: string): string {
	const pattern = new RegExp(escapeRegExp(rawTerm), 'i');
	return normalizeWhitespace(question.replace(pattern, replacement));
}

function buildNameMismatchSuggestions(
	locale: Locale,
	question: string,
	mismatch: NameMismatchResult
): QuestionSuggestion[] {
	const primary = mismatch.matches[0];
	const focus = questionFocus(question, locale);
	const rewritten = rewriteQuestion(question, mismatch.term, primary.name);
	const suggestions: QuestionSuggestion[] = [
		{ text: rewritten, sourceId: primary.id }
	];
	if (locale === 'ja') {
		suggestions.push(
			{
				text:
					focus.length > 0
						? `${primary.name} で ${focus} だけ教えてください。`
						: `${primary.name} の要点を教えてください。`,
				sourceId: primary.id
			},
			{
				text: `${primary.name} の中で答えに使える箇所を短く教えてください。`,
				sourceId: primary.id
			}
		);
		if (mismatch.matches[1]) {
			suggestions.push({
				text: `${mismatch.matches[1].name} では同じ点がどう書かれていますか？`,
				sourceId: mismatch.matches[1].id
			});
		}
	} else {
		suggestions.push(
			{
				text:
					focus.length > 0
						? `What does ${primary.name} say about ${focus}?`
						: `What are the key points in ${primary.name}?`,
				sourceId: primary.id
			},
			{
				text: `Show only the part of ${primary.name} that can support the answer.`,
				sourceId: primary.id
			}
		);
		if (mismatch.matches[1]) {
			suggestions.push({
				text: `How does ${mismatch.matches[1].name} describe the same point?`,
				sourceId: mismatch.matches[1].id
			});
		}
	}
	return dedupeSuggestions(suggestions).slice(0, 3);
}

function hasSpecificDocumentAnchor(question: string, sources: RagSourceItem[]): boolean {
	const normalizedQuestion = normalizeLookup(question);
	if (!normalizedQuestion) {
		return false;
	}
	return sources.some((item) => {
		const nameNorm = normalizeLookup(item.name);
		const baseNorm = normalizeLookup(basenameLike(item.path));
		return (
			(nameNorm.length > 0 && normalizedQuestion.includes(nameNorm)) ||
			(baseNorm.length > 0 && normalizedQuestion.includes(baseNorm))
		);
	});
}

function hasSpecificTopicAnchor(question: string): boolean {
	return (
		/main path|documents|questions|evidence|api|constraint|design|architecture/i.test(question) ||
		/画面|制約|設計|根拠|要件|証拠|構成|main path/.test(question)
	);
}

function resultHasNotice(result: PresentedQuestionRun | null, code: QuestionNoticeCode): boolean {
	return result?.notices.includes(code) ?? false;
}

function isTooBroadQuestion(
	question: string,
	sources: RagSourceItem[],
	selectedScopeId: string | null,
	result: PresentedQuestionRun | null
): boolean {
	const compact = normalizeWhitespace(question);
	if (!compact) {
		return false;
	}
	const tokenCount = tokenizeForOverlap(compact).length;
	const broadPhrase =
		/要点|概要|まとめ|全部|全体|重要なこと|何が書いてある|教えて|知りたい|summary|overview|everything|important|tell me about/i;
	if (resultHasNotice(result, 'clarify_question')) {
		return true;
	}
	if (selectedScopeId) {
		return tokenCount <= 3 && broadPhrase.test(compact);
	}
	if (hasSpecificDocumentAnchor(compact, sources) || hasSpecificTopicAnchor(compact)) {
		return false;
	}
	return broadPhrase.test(compact) || tokenCount <= 4;
}

function weakEvidenceSuggestions(
	locale: Locale,
	sources: RagSourceItem[],
	selectedScopeId: string | null,
	question: string
): QuestionSuggestion[] {
	const focus = questionFocus(question, locale);
	const targetSources = sourceById(sources, selectedScopeId)
		? [sourceById(sources, selectedScopeId) as RagSourceItem]
		: enabledSourcesOnly(sources).slice(0, 2);
	const out: QuestionSuggestion[] = [];
	for (const item of targetSources) {
		const label = displayLabel(item);
		if (locale === 'ja') {
			out.push(
				{
					text:
						focus.length > 0
							? `${label} の中で ${focus} に触れている点だけ教えてください。`
							: `${label} の中で答えに使える点だけ教えてください。`,
					sourceId: item.id
				},
				{
					text: `${label} で答えられる範囲だけ短く教えてください。`,
					sourceId: item.id
				}
			);
		} else {
			out.push(
				{
					text:
						focus.length > 0
							? `Show only the part of ${label} that mentions ${focus}.`
							: `Show only the part of ${label} that can support the answer.`,
					sourceId: item.id
				},
				{
					text: `Answer only the part that ${label} can support.`,
					sourceId: item.id
				}
			);
		}
	}
	return dedupeSuggestions(out).slice(0, 3);
}

export function deriveQuestionScopeChips(
	sources: RagSourceItem[],
	locale: Locale
): QuestionScopeChip[] {
	return [
		{
			label: locale === 'ja' ? '指定しない' : 'No scope',
			sourceId: null
		},
		...enabledSourcesOnly(sources).slice(0, 4).map((item) => ({
			label: displayLabel(item),
			sourceId: item.id
		}))
	];
}

export function deriveQuestionExamples(
	sources: RagSourceItem[],
	locale: Locale,
	selectedScopeId: string | null
): QuestionSuggestion[] {
	const enabled = enabledSourcesOnly(sources);
	const scoped = sourceById(enabled, selectedScopeId);
	if (scoped) {
		return dedupeSuggestions(exampleTemplatesForSource(scoped, locale)).slice(0, 5);
	}
	const out: QuestionSuggestion[] = [];
	for (const item of enabled.slice(0, 3)) {
		out.push(exampleTemplatesForSource(item, locale)[0]);
	}
	if (out.length < 3 && enabled[0]) {
		out.push(...exampleTemplatesForSource(enabled[0], locale).slice(1, 3));
	}
	if (out.length < 4 && enabled[1]) {
		out.push(...exampleTemplatesForSource(enabled[1], locale).slice(1, 2));
	}
	return dedupeSuggestions(out).slice(0, 5);
}

export function buildQuestionGuidance(input: BuildGuidanceInput): QuestionGuidance {
	const question = normalizeWhitespace(input.question);
	const sources = enabledSourcesOnly(input.sources);
	if (input.uiState === 'idle') {
		return {
			kind: 'idle',
			diagnosis: '',
			reaskSuggestions: [],
			likelyMatches: []
		};
	}
	if (input.uiState === 'answer') {
		return {
			kind: 'answer_ready',
			diagnosis: '',
			reaskSuggestions: [],
			likelyMatches: []
		};
	}
	if (input.uiState === 'blank') {
		return {
			kind: 'blank_input',
			diagnosis:
				input.locale === 'ja'
					? 'まだ質問が空です。いつもの言い方で 1 つだけ聞いてください。'
					: 'The question is still blank. Ask one thing in ordinary language first.',
			reaskSuggestions: deriveQuestionExamples(sources, input.locale, input.selectedScopeId).slice(0, 3),
			likelyMatches: []
		};
	}
	if (input.uiState === 'no_documents') {
		return {
			kind: 'no_documents',
			diagnosis:
				input.locale === 'ja'
					? '今は参照できる資料がありません。まず Documents で資料をそろえてください。'
					: 'There are no documents available yet. Add documents in Documents first.',
			reaskSuggestions: [],
			likelyMatches: []
		};
	}
	if (input.uiState === 'backend_unavailable') {
		return {
			kind: 'backend_unavailable',
			diagnosis:
				input.locale === 'ja'
					? 'いまはモデルかバックエンドに接続できません。質問の言い方ではなく接続状態の問題です。'
					: 'The model or backend is unavailable right now. This is a connectivity problem, not a wording problem.',
			reaskSuggestions: [],
			likelyMatches: []
		};
	}
	if (input.uiState === 'server_failure') {
		return {
			kind: 'server_failure',
			diagnosis:
				input.locale === 'ja'
					? 'サーバー処理に失敗しました。質問はそのままで、少し待ってから再実行してください。'
					: 'The server failed while processing the request. Keep the question and try again in a moment.',
			reaskSuggestions: [],
			likelyMatches: []
		};
	}

	const mismatch = detectNameMismatch(question, sources);
	if (mismatch) {
		const primary = mismatch.matches[0];
		return {
			kind: 'name_mismatch',
			diagnosis:
				input.locale === 'ja'
					? `「${mismatch.term}」という表記に近い現在の資料は『${primary.name}』です。正確な資料名を覚えていなくても大丈夫ですが、近い名前に寄せると答えやすくなります。`
					: `The wording "${mismatch.term}" does not match a current document name exactly. The closest current document is "${primary.name}", and using that name will make the question easier to answer.`,
			reaskSuggestions: buildNameMismatchSuggestions(input.locale, question, mismatch),
			likelyMatches: mismatch.matches
		};
	}

	if (isTooBroadQuestion(question, sources, input.selectedScopeId, input.result)) {
		return {
			kind: 'too_broad',
			diagnosis:
				input.locale === 'ja'
					? '質問の範囲がまだ広く、どの資料のどの論点を見るか絞り切れていません。1 つの資料か 1 つの論点に寄せると答えやすくなります。'
					: 'The question is still too broad, so the system cannot narrow it to one document or one point yet. Narrowing it to one document or one topic will make it easier to answer.',
			reaskSuggestions: deriveQuestionExamples(sources, input.locale, input.selectedScopeId).slice(0, 3),
			likelyMatches: []
		};
	}

	return {
		kind: 'weak_evidence',
		diagnosis:
			input.locale === 'ja'
				? '関連しそうな資料候補はありますが、この質問に答え切るには根拠がまだ弱いです。答えたい範囲を少し狭めると通りやすくなります。'
				: 'There are related document candidates, but the support is still too weak to answer this question directly. Narrowing the target a little should help.',
		reaskSuggestions: weakEvidenceSuggestions(
			input.locale,
			sources,
			input.selectedScopeId,
			question
		),
		likelyMatches: []
	};
}
