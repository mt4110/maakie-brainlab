import { json } from '@sveltejs/kit';

import { writeRagDataAndRebuild } from '$lib/server/rag-lab-data';

export async function POST({ request }: { request: Request }) {
	let body: {
		fileName?: string;
		content?: string;
		rebuildIndex?: boolean;
	};
	try {
		body = (await request.json()) as typeof body;
	} catch {
		return json({ error: 'Invalid JSON body.' }, { status: 400 });
	}

	try {
		const payload = await writeRagDataAndRebuild({
			fileName: String(body.fileName || ''),
			content: String(body.content || ''),
			rebuildIndex: body.rebuildIndex !== false
		});
		return json(payload);
	} catch (error) {
		return json(
			{
				error: error instanceof Error ? error.message : 'Failed to add RAG data.'
			},
			{ status: 400 }
		);
	}
}
