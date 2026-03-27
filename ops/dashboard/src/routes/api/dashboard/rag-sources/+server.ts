import { json } from '@sveltejs/kit';

import { createRagSource, queryRagSources } from '$lib/server/chat-rag-data';
import type { RagSourceCreateRequest } from '$lib/server/types';

export async function GET({ url }: { url: URL }) {
	const query = url.searchParams.get('q') || '';
	const page = Number(url.searchParams.get('page') || '1');
	const pageSize = Number(url.searchParams.get('pageSize') || '12');
	const payload = await queryRagSources({
		query,
		page: Number.isFinite(page) ? page : 1,
		pageSize: Number.isFinite(pageSize) ? pageSize : 12
	});
	return json(payload);
}

export async function POST({ request }: { request: Request }) {
	let body: RagSourceCreateRequest;
	try {
		body = (await request.json()) as RagSourceCreateRequest;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}
	try {
		const item = await createRagSource(body);
		return json({ item }, { status: 201 });
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Failed to create RAG source.'
			},
			{ status: 400 }
		);
	}
}
