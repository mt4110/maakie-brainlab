import type { ChatRunResponse, RagSuggestion, RunInspectorRetrieval } from '$lib/server/types';

export type QuestionsFailureKind = 'backend_unavailable' | 'server_failure';
export type QuestionPresentationKind = 'answer' | 'unknown';
export type QuestionNoticeCode =
	| 'candidate_evidence_only'
	| 'no_matching_documents'
	| 'clarify_question'
	| 'verify_before_reuse';
export type QuestionEvidenceMatchKind =
	| 'selected'
	| 'name'
	| 'tag'
	| 'path'
	| 'description'
	| 'retrieval';

export interface QuestionEvidenceMatch {
	kind: QuestionEvidenceMatchKind;
	term: string | null;
}

export interface QuestionEvidenceItem {
	sourceId: string;
	sourceName: string;
	sourcePath: string;
	preview: string;
	matches: QuestionEvidenceMatch[];
}

export interface QuestionDocumentItem {
	id: string;
	name: string;
	path: string;
}

export interface PresentedQuestionRun {
	kind: QuestionPresentationKind;
	answer: string;
	evidence: QuestionEvidenceItem[];
	documentsUsed: QuestionDocumentItem[];
	notices: QuestionNoticeCode[];
}

function normalizeText(value: string): string {
	return value.replace(/\s+/g, ' ').trim();
}

function firstParagraph(text: string): string {
	const chunks = text
		.split(/\n\s*\n/)
		.map((item) => normalizeText(item))
		.filter(Boolean);
	return chunks[0] ?? '';
}

function fallbackName(pathLike: string): string {
	const compact = normalizeText(pathLike);
	if (!compact) {
		return 'Related document';
	}
	const parts = compact.split('/').filter(Boolean);
	return parts[parts.length - 1] || compact;
}

function parseReasonToken(token: string): QuestionEvidenceMatch | null {
	const compact = normalizeText(token);
	if (!compact) {
		return null;
	}
	if (compact === 'selected') {
		return { kind: 'selected', term: null };
	}
	const separator = compact.indexOf(':');
	if (separator <= 0) {
		return { kind: 'retrieval', term: compact };
	}
	const kind = compact.slice(0, separator).trim();
	const term = compact.slice(separator + 1).trim() || null;
	switch (kind) {
		case 'name':
			return { kind: 'name', term };
		case 'tag':
			return { kind: 'tag', term };
		case 'path':
			return { kind: 'path', term };
		case 'desc':
			return { kind: 'description', term };
		default:
			return { kind: 'retrieval', term: compact };
	}
}

function mergeMatches(
	current: QuestionEvidenceMatch[],
	incoming: QuestionEvidenceMatch[]
): QuestionEvidenceMatch[] {
	const merged = [...current];
	for (const item of incoming) {
		const exists = merged.some((row) => row.kind === item.kind && row.term === item.term);
		if (!exists) {
			merged.push(item);
		}
	}
	return merged;
}

function parseReasonText(raw: string): QuestionEvidenceMatch[] {
	return raw
		.split(',')
		.map((item) => parseReasonToken(item))
		.filter((item): item is QuestionEvidenceMatch => item !== null);
}

function looksUnknownText(text: string): boolean {
	const compact = text.toLowerCase();
	if (!compact) {
		return true;
	}
	return (
		/不明|分かりません|わかりません|判断できません|確認できません|資料が足りません|根拠が足りません/.test(
			text
		) ||
		/not enough|insufficient|cannot determine|unable to determine|unknown|need more context|no evidence/.test(
			compact
		)
	);
}

function needsClarification(text: string): boolean {
	const compact = text.toLowerCase();
	return (
		/具体的|詳しい|ファイル名|対象|期間|絞/.test(text) ||
		/more specific|clarify|which document|what time range|need the file name/.test(compact)
	);
}

function suggestionToDocument(item: RagSuggestion): QuestionDocumentItem {
	return {
		id: item.id,
		name: item.name,
		path: item.path
	};
}

function retrievalKey(item: RunInspectorRetrieval): string {
	return normalizeText(item.sourcePath) || normalizeText(item.sourceId);
}

export function classifyChatRunFailure(message: string): QuestionsFailureKind {
	const compact = message.toLowerCase();
	if (
		/endpoint not found|network_error|fetch failed|econnrefused|connection refused|apiBase=|chat\/completions/.test(
			compact
		)
	) {
		return 'backend_unavailable';
	}
	if (/gemma-lab|gemma bridge/.test(compact)) {
		return 'backend_unavailable';
	}
	return 'server_failure';
}

export function presentQuestionRun(payload: ChatRunResponse): PresentedQuestionRun {
	const suggestions = payload.ragSuggestions || [];
	const suggestionById = new Map(suggestions.map((item) => [item.id, item] as const));
	const suggestionByPath = new Map(
		suggestions
			.filter((item) => normalizeText(item.path))
			.map((item) => [normalizeText(item.path), item] as const)
	);
	const evidenceByKey = new Map<string, QuestionEvidenceItem>();
	const retrievals = payload.inspector?.retrievals || [];

	for (const item of retrievals) {
		const key = retrievalKey(item);
		const suggestion =
			suggestionById.get(item.sourceId) || suggestionByPath.get(normalizeText(item.sourcePath));
		const sourceName =
			normalizeText(suggestion?.name || '') ||
			normalizeText(item.chunkText) ||
			fallbackName(item.sourcePath);
		const preview =
			normalizeText(item.chunkText) && normalizeText(item.chunkText) !== sourceName
				? normalizeText(item.chunkText)
				: '';
		const existing = evidenceByKey.get(key);
		const matches = mergeMatches(
			existing?.matches || [],
			parseReasonText(item.reason || 'retrieval')
		);
		evidenceByKey.set(key, {
			sourceId: normalizeText(item.sourceId) || suggestion?.id || key,
			sourceName,
			sourcePath: normalizeText(item.sourcePath),
			preview,
			matches: matches.length > 0 ? matches : [{ kind: 'retrieval', term: null }]
		});
	}

	for (const item of suggestions) {
		const key = normalizeText(item.path) || item.id;
		const existing = evidenceByKey.get(key);
		const matches = mergeMatches(existing?.matches || [], parseReasonText(item.reason || ''));
		evidenceByKey.set(key, {
			sourceId: item.id,
			sourceName: item.name,
			sourcePath: item.path,
			preview: existing?.preview || '',
			matches
		});
	}

	const evidence = Array.from(evidenceByKey.values()).slice(0, 5);
	const documentMap = new Map<string, QuestionDocumentItem>();
	for (const item of suggestions) {
		documentMap.set(item.id, suggestionToDocument(item));
	}
	for (const item of evidence) {
		if (!documentMap.has(item.sourceId)) {
			documentMap.set(item.sourceId, {
				id: item.sourceId,
				name: item.sourceName,
				path: item.sourcePath
			});
		}
	}

	const documentsUsed = Array.from(documentMap.values()).slice(0, 5);
	const answer = firstParagraph(payload.assistantMessage || '');
	const unknown = evidence.length === 0 || looksUnknownText(answer);
	const suppressUnsupportedAnswer = unknown && evidence.length === 0 && !looksUnknownText(answer);
	const notices: QuestionNoticeCode[] = [];

	if (evidence.length > 0) {
		notices.push('candidate_evidence_only');
	}
	if (documentsUsed.length === 0) {
		notices.push('no_matching_documents');
	}
	if (needsClarification(payload.assistantMessage || '')) {
		notices.push('clarify_question');
	}
	if (!unknown && evidence.length > 0) {
		notices.push('verify_before_reuse');
	}

	return {
		kind: unknown ? 'unknown' : 'answer',
		answer: suppressUnsupportedAnswer ? '' : answer,
		evidence,
		documentsUsed,
		notices
	};
}
