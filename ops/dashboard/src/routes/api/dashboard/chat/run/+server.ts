import { json } from '@sveltejs/kit';

import { runChatWithRag } from '$lib/server/chat-rag-data';
import type { ChatRunRequest } from '$lib/server/types';

export async function POST({ request }: { request: Request }) {
	let body: ChatRunRequest;
	try {
		body = (await request.json()) as ChatRunRequest;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}
	try {
		const payload = await runChatWithRag(body);
		return json(payload);
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Chat execution failed.'
			},
			{ status: 500 }
		);
	}
}
