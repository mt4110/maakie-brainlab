import { json } from '@sveltejs/kit';

import { runAiLab } from '$lib/server/lab-data';
import type { AiLabChannel, AiLabRunRequest } from '$lib/server/types';

const VALID_CHANNELS: AiLabChannel[] = [
	'local-model',
	'mcp',
	'ai-cli',
	'fine-tune',
	'rag-tuning',
	'langchain'
];

function isValidChannel(value: string): value is AiLabChannel {
	return VALID_CHANNELS.includes(value as AiLabChannel);
}

export async function POST({ request }: { request: Request }) {
	let body: AiLabRunRequest;
	try {
		body = (await request.json()) as AiLabRunRequest;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}

	const channel = String(body.channel || '').trim();
	if (!isValidChannel(channel)) {
		return json(
			{ error: `channel must be one of: ${VALID_CHANNELS.join(', ')}` },
			{ status: 400 }
		);
	}

	try {
		const payload = await runAiLab({ ...body, channel });
		return json(payload);
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'AI lab execution failed.'
			},
			{ status: 500 }
		);
	}
}
