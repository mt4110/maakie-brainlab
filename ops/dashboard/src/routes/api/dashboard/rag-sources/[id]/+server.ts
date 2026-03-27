import { json } from '@sveltejs/kit';

import { deleteRagSource, updateRagSource } from '$lib/server/chat-rag-data';
import type { RagSourceUpdateRequest } from '$lib/server/types';

export async function PATCH({ params, request }: { params: { id: string }; request: Request }) {
	let body: RagSourceUpdateRequest;
	try {
		body = (await request.json()) as RagSourceUpdateRequest;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}
	try {
		const item = await updateRagSource(params.id, body);
		if (!item) {
			return json({ error: 'RAG source not found.' }, { status: 404 });
		}
		return json({ item });
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Failed to update RAG source.'
			},
			{ status: 400 }
		);
	}
}

export async function DELETE({ params }: { params: { id: string } }) {
	const ok = await deleteRagSource(params.id);
	if (!ok) {
		return json({ error: 'RAG source not found.' }, { status: 404 });
	}
	return json({ status: 'deleted' });
}
