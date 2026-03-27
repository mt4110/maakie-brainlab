import { asString } from './fs';

export interface OpenAiCompatMessage {
	role: string;
	content: string;
}

export interface OpenAiCompatChatRequest {
	apiBase: string;
	apiKey: string;
	model: string;
	temperature: number;
	messages: OpenAiCompatMessage[];
}

export interface OpenAiCompatChatResponse {
	content: string;
	resolvedUrl: string;
}

const DEFAULT_OPENAI_COMPAT_API_BASE = 'http://127.0.0.1:11434/v1';

function trimOneLine(value: string, limit = 180): string {
	const text = value.replace(/\s+/g, ' ').trim();
	if (text.length <= limit) {
		return text;
	}
	return `${text.slice(0, limit).trimEnd()}...`;
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

export function resolveOpenAiCompatApiBase(apiBase: string | undefined | null): string {
	const candidate = asString(apiBase).trim();
	if (candidate) {
		return candidate;
	}
	const fromEnv = asString(process.env.OPENAI_API_BASE).trim();
	if (fromEnv) {
		return fromEnv;
	}
	return DEFAULT_OPENAI_COMPAT_API_BASE;
}

export function chatCompletionUrlCandidates(apiBase: string): string[] {
	let base = resolveOpenAiCompatApiBase(apiBase).replace(/\/+$/, '');
	if (base.endsWith('/chat/completions')) {
		base = base.slice(0, -'/chat/completions'.length).replace(/\/+$/, '');
	}

	const candidates = [`${base}/chat/completions`];
	if (base.endsWith('/v1')) {
		const root = base.slice(0, -'/v1'.length).replace(/\/+$/, '');
		if (root) {
			candidates.push(`${root}/chat/completions`);
		}
	} else {
		candidates.push(`${base}/v1/chat/completions`);
	}
	return dedupeKeepOrder(candidates);
}

function parseChatContent(raw: string): string {
	const text = raw.trim();
	if (!text) {
		return '';
	}
	try {
		const parsed = JSON.parse(raw) as {
			choices?: Array<{ message?: { content?: string } }>;
			message?: { content?: string };
			response?: string;
		};
		const choicesContent = asString(parsed.choices?.[0]?.message?.content).trim();
		if (choicesContent) {
			return choicesContent;
		}
		const messageContent = asString(parsed.message?.content).trim();
		if (messageContent) {
			return messageContent;
		}
		const responseContent = asString(parsed.response).trim();
		if (responseContent) {
			return responseContent;
		}
	} catch {
		// fallback to raw plain text
	}
	return text;
}

export async function postOpenAiCompatChat(
	request: OpenAiCompatChatRequest
): Promise<OpenAiCompatChatResponse> {
	const urls = chatCompletionUrlCandidates(request.apiBase);
	const attempts: string[] = [];
	for (const url of urls) {
		let response: globalThis.Response;
		try {
			response = await fetch(url, {
				method: 'POST',
				headers: {
					'content-type': 'application/json',
					authorization: `Bearer ${request.apiKey || 'dummy'}`
				},
				body: JSON.stringify({
					model: request.model,
					temperature: request.temperature,
					messages: request.messages
				})
			});
		} catch (error) {
			const detail = trimOneLine(error instanceof Error ? error.message : String(error), 120);
			attempts.push(`${url} -> network_error: ${detail}`);
			continue;
		}

		const raw = (await response.text()) || '';
		if (response.status === 404) {
			attempts.push(`${url} -> 404`);
			continue;
		}
		if (!response.ok) {
			throw new Error(
				`chat api error status=${response.status} url=${url} detail=${trimOneLine(raw)}`
			);
		}
		const content = parseChatContent(raw);
		if (!content.trim()) {
			throw new Error(`chat api returned empty content: ${url}`);
		}
		return { content, resolvedUrl: url };
	}

	throw new Error(
		`openai-compatible endpoint not found for apiBase=${resolveOpenAiCompatApiBase(request.apiBase)}; ` +
			`attempts=[${attempts.join('; ') || 'none'}]. ` +
			'Use an LLM endpoint such as http://127.0.0.1:11434/v1.'
	);
}
